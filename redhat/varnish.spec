%define v_rc beta1
%define vd_rc %{?v_rc:-%{?v_rc}}
%define    _use_internal_dependency_generator 0
%define __find_provides %{_builddir}/../SOURCES/find-provides
%define debug_package %{nil}
%define _enable_debug_package 0
%define __os_install_post /usr/lib/rpm/brp-compress %{nil}

Summary: High-performance HTTP accelerator
Name: varnish
Version: 3.0.0
#Release: 0.20140328%{?v_rc}%{?dist}
Release: 1%{?v_rc}%{?dist}
License: BSD
Group: System Environment/Daemons
URL: https://www.varnish-cache.org/
#Source0: http://repo.varnish-cache.org/source/%{name}-%{version}.tar.gz
Source0: %{name}-%{version}%{?vd_rc}.tar.gz
Source1: varnish.initrc
Source2: varnish.sysconfig
Source3: varnish.logrotate
Source4: varnish_reload_vcl
Source5: varnish.params
Source6: varnish.service
Source9: varnishncsa.initrc
Source10: varnishncsa.service
Source11: find-provides

BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildRequires: automake
BuildRequires: autoconf
BuildRequires: jemalloc-devel
BuildRequires: libedit-devel
BuildRequires: libtool
BuildRequires: ncurses-devel
BuildRequires: pcre-devel
BuildRequires: pkgconfig
BuildRequires: python-docutils >= 0.6
BuildRequires: python-sphinx
Requires: jemalloc
Requires: libedit
Requires: logrotate
Requires: ncurses
Requires: pcre
Requires(pre): shadow-utils
Requires(post): /sbin/chkconfig, /usr/bin/uuidgen
Requires(preun): /sbin/chkconfig
Requires(preun): /sbin/service
%if %{undefined suse_version}
Requires(preun): initscripts
%endif
%if 0%{?fedora} >= 17 || 0%{?rhel} >= 7
Requires(post): systemd-units
Requires(post): systemd-sysv
Requires(preun): systemd-units
Requires(postun): systemd-units
BuildRequires: systemd-units
%endif
Requires: gcc
Provides: varnish-libs
Obsoletes: varnish-libs
Conflicts: varnish-libs

%description
This is Varnish Cache, a high-performance HTTP accelerator.

Varnish Cache stores web pages in memory so web servers don't have to
create the same web page over and over again. Varnish Cache serves
pages much faster than any application server; giving the website a
significant speed up.

Documentation wiki and additional information about Varnish Cache is
available on the following web site: https://www.varnish-cache.org/

%package devel
Summary: Development files for %{name}
Group: System Environment/Libraries
BuildRequires: ncurses-devel
Provides: varnish-libs-devel
Obsoletes: varnish-libs-devel
Conflicts: varnish-libs-devel
Requires: varnish = %{version}-%{release}
Requires: pkgconfig
Requires: python

%description devel
Development files for %{name}-libs
Varnish Cache is a high-performance HTTP accelerator

%prep
%setup -n varnish-%{version}%{?vd_rc}
#%setup -q -n varnish-trunk
cp %{SOURCE1} %{SOURCE2} %{SOURCE3} %{SOURCE4} %{SOURCE5} .
cp %{SOURCE6} %{SOURCE9} %{SOURCE10} %{SOURCE11} .

%build
# No pkgconfig/libpcre.pc in rhel4
%if 0%{?rhel} == 4
	export PCRE_CFLAGS="`pcre-config --cflags`"
	export PCRE_LIBS="`pcre-config --libs`"
%endif

%if 0%{?rhel} == 6
export CFLAGS="$CFLAGS -O2 -g -Wp,-D_FORTIFY_SOURCE=0"
%endif

# jemalloc is not compatible with Red Hat's ppc64 RHEL kernel :-(
%ifarch ppc64 ppc
	%configure --localstatedir=/var/lib --without-jemalloc --without-rst2html
%else
	%configure --localstatedir=/var/lib --without-rst2html
%endif

# We have to remove rpath - not allowed in Fedora
# (This problem only visible on 64 bit arches)
#sed -i 's|^hardcode_libdir_flag_spec=.*|hardcode_libdir_flag_spec=""|g;
#	s|^runpath_var=LD_RUN_PATH|runpath_var=DIE_RPATH_DIE|g' libtool

make %{?_smp_mflags} V=1

%if 0%{?fedora}%{?rhel} != 0 && 0%{?rhel} <= 4 && 0%{?fedora} <= 8
	# Old style daemon function
	sed -i 's,--pidfile \$pidfile,,g;
		s,status -p \$pidfile,status,g;
		s,killproc -p \$pidfile,killproc,g' \
	varnish.initrc varnishncsa.initrc
%endif

# In 4.0 the built docs need to be copied to the current/4.1 location.
test -d doc/html || cp -pr doc/sphinx/build/html doc/html

rm -rf doc/html/_sources
#rm -rf doc/sphinx/build/html/_sources
#mv doc/sphinx/build/html doc
rm -rf doc/sphinx/build

%check
# rhel5 on ppc64 is just too strange
%ifarch ppc64
	%if 0%{?rhel} > 4
		cp bin/varnishd/.libs/varnishd bin/varnishd/lt-varnishd
	%endif
%endif

# The redhat ppc builders seem to have some ulimit problems?
# These tests work on a rhel4 ppc/ppc64 instance outside the builders
%ifarch ppc64 ppc
	%if 0%{?rhel} == 4
		rm bin/varnishtest/tests/c00031.vtc
		rm bin/varnishtest/tests/r00387.vtc
	%endif
%endif

make check %{?_smp_mflags} LD_LIBRARY_PATH="../../lib/libvarnish/.libs:../../lib/libvarnishcompat/.libs:../../lib/libvarnishapi/.libs:../../lib/libvcc/.libs:../../lib/libvgz/.libs" VERBOSE=1

%install
rm -rf %{buildroot}
make install DESTDIR=%{buildroot} INSTALL="install -p"

# None of these for fedora
find %{buildroot}/%{_libdir}/ -name '*.la' -exec rm -f {} ';'

# Remove this line to build a devel package with symlinks
#find %{buildroot}/%{_libdir}/ -name '*.so' -type l -exec rm -f {} ';'

mkdir -p %{buildroot}/var/lib/varnish
mkdir -p %{buildroot}/var/log/varnish
mkdir -p %{buildroot}/var/run/varnish
mkdir -p %{buildroot}%{_sysconfdir}/ld.so.conf.d/
install -D -m 0644 etc/example.vcl %{buildroot}%{_sysconfdir}/varnish/default.vcl
install -D -m 0644 varnish.logrotate %{buildroot}%{_sysconfdir}/logrotate.d/varnish

# systemd support
%if 0%{?fedora} >= 17 || 0%{?rhel} >= 7
mkdir -p %{buildroot}%{_unitdir}
install -D -m 0644 varnish.service %{buildroot}%{_unitdir}/varnish.service
install -D -m 0644 varnish.params %{buildroot}%{_sysconfdir}/varnish/varnish.params
install -D -m 0644 varnishncsa.service %{buildroot}%{_unitdir}/varnishncsa.service
sed -i 's,sysconfig/varnish,varnish/varnish.params,' varnish_reload_vcl
# default is standard sysvinit
%else
install -D -m 0644 varnish.sysconfig %{buildroot}%{_sysconfdir}/sysconfig/varnish
install -D -m 0755 varnish.initrc %{buildroot}%{_initrddir}/varnish
install -D -m 0755 varnishncsa.initrc %{buildroot}%{_initrddir}/varnishncsa
%endif
install -D -m 0755 varnish_reload_vcl %{buildroot}%{_sbindir}/varnish_reload_vcl

echo %{_libdir}/varnish > %{buildroot}%{_sysconfdir}/ld.so.conf.d/varnish-%{_arch}.conf

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%{_sbindir}/*
%{_bindir}/*
%{_var}/lib/varnish
%{_var}/log/varnish
%{_mandir}/man1/*.1*
%{_mandir}/man3/*.3*
%{_mandir}/man7/*.7*
%{_docdir}/varnish/
%doc doc/html
%doc doc/changes*.html
%dir %{_sysconfdir}/varnish/
%config(noreplace) %{_sysconfdir}/varnish/default.vcl
%config(noreplace) %{_sysconfdir}/logrotate.d/varnish

# systemd from fedora 17 and rhel 7
%if 0%{?fedora} >= 17 || 0%{?rhel} >= 7
%{_unitdir}/varnish.service
%{_unitdir}/varnishncsa.service
%config(noreplace)%{_sysconfdir}/varnish/varnish.params

# default is standard sysvinit
%else
%config(noreplace) %{_sysconfdir}/sysconfig/varnish
%{_initrddir}/varnish
%{_initrddir}/varnishncsa
%endif

%defattr(-,root,root,-)
%{_libdir}/*.so.*
%{_libdir}/varnish
%doc LICENSE
%config %{_sysconfdir}/ld.so.conf.d/varnish-%{_arch}.conf

%files devel
%defattr(-,root,root,-)
%{_libdir}/lib*.so
%dir %{_includedir}/varnish
%{_includedir}/varnish/*
%{_libdir}/pkgconfig/varnishapi.pc
/usr/share/varnish
/usr/share/aclocal
%doc LICENSE


%pre
getent group varnish    >/dev/null || groupadd -r varnish
getent passwd varnishlog >/dev/null || \
	useradd -r -g varnish -d /dev/null -s /sbin/nologin \
		-c "varnishlog user" varnishlog
getent passwd varnish >/dev/null || \
	useradd -r -g varnish -d /var/lib/varnish -s /sbin/nologin \
		-c "Varnish Cache" varnish
exit 0

%post
%if 0%{?fedora} >= 17 || 0%{?rhel} >= 7
/bin/systemctl daemon-reload >/dev/null 2>&1 || :
%else
/sbin/chkconfig --add varnish
/sbin/chkconfig --add varnishncsa
%endif

test -f /etc/varnish/secret || (uuidgen > /etc/varnish/secret && chmod 0600 /etc/varnish/secret)
chown varnishlog:varnish /var/log/varnish/
/sbin/ldconfig

%triggerun -- varnish < 3.0.2-1
# Save the current service runlevel info
# User must manually run systemd-sysv-convert --apply varnish
# to migrate them to systemd targets
%{_bindir}/systemd-sysv-convert --save varnish >/dev/null 2>&1 ||:

# If the package is allowed to autostart:
#/bin/systemctl --no-reload enable varnish.service >/dev/null 2>&1 ||:

# Run these because the SysV package being removed won't do them
/sbin/chkconfig --del varnish >/dev/null 2>&1 || :
#/bin/systemctl try-restart varnish.service >/dev/null 2>&1 || :

%preun
if [ $1 -lt 1 ]; then
  # Package removal, not upgrade
  %if 0%{?fedora} >= 17 || 0%{?rhel} >= 7
  /bin/systemctl --no-reload disable varnish.service > /dev/null 2>&1 || :
  /bin/systemctl stop varnish.service > /dev/null 2>&1 || :
  /bin/systemctl stop varnishncsa.service > /dev/null 2>&1 || :
  %else
  /sbin/service varnish stop > /dev/null 2>&1
  /sbin/service varnishncsa stop > /dev/null 2>%1
  /sbin/chkconfig --del varnish
  /sbin/chkconfig --del varnishncsa
  %endif
fi

%postun -p /sbin/ldconfig

%changelog
* Thu Jul 24 2014 Varnish Software <opensource@varnish-software.com> - 3.0.0-1
- This changelog is not in use. See doc/changes.rst for release notes.

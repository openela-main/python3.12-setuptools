%global __python3 /usr/bin/python3.12
%global python3_pkgversion 3.12

%global srcname setuptools

# used when bootstrapping new Python versions
%bcond_with bootstrap

# Similar to what we have in pythonX.Y.spec files.
# If enabled, provides unversioned executables and other stuff.
# Disable it if you build this package in an alternative stack.
%bcond_with main_python

# Some dependencies are missing on RHEL, hence tests are disabled by default
%bcond_with tests

%global python_wheel_name %{srcname}-%{version}-py3-none-any.whl

Name:           python%{python3_pkgversion}-setuptools
# When updating, update the bundled libraries versions bellow!
Version:        68.2.2
Release:        3%{?dist}
Summary:        Easily build and distribute Python packages
# setuptools is MIT
# platformdirs is MIT
# more-itertools is MIT
# ordered-set is MIT
# packaging is BSD or ASL 2.0
# importlib-metadata is ASL 2.0
# importlib-resources is ASL 2.0
# jaraco.text is MIT
# typing-extensions is Python
# zipp is MIT
# nspektr is MIT
# tomli is MIT
# the setuptools logo is MIT
License:        MIT and ASL 2.0 and (BSD or ASL 2.0) and Python
URL:            https://pypi.python.org/pypi/%{srcname}
Source0:        %{pypi_source %{srcname} %{version}}

# The `setup.py install` deprecation notice might be confusing for RPM packagers
# adjust it, but only when $RPM_BUILD_ROOT is set
Patch:          Adjust-the-setup.py-install-deprecation-message.patch

BuildArch:      noarch

BuildRequires:  python%{python3_pkgversion}-devel
BuildRequires:  python%{python3_pkgversion}-rpm-macros

%if %{with tests}
BuildRequires:  gcc
%endif

# python3 bootstrap: this is built before the final build of python3, which
# adds the dependency on python3-rpm-generators, so we require it manually
BuildRequires:  python3-rpm-generators

%if %{without bootstrap}
BuildRequires:  python%{python3_pkgversion}-pip
BuildRequires:  python%{python3_pkgversion}-wheel
# Not to use the pre-generated egg-info, we use setuptools from previous build to generate it
BuildRequires:  python%{python3_pkgversion}-setuptools
%endif

# Virtual provides for the packages bundled by setuptools.
# Bundled packages are defined in multiple files. Generate the list with:
# %%{_rpmconfigdir}/pythonbundles.py --namespace 'python%%{python3_pkgversion}dist' */_vendor/vendored.txt
%global bundled %{expand:
Provides: bundled(python%{python3_pkgversion}dist(platformdirs)) = 2.6.2
Provides: bundled(python%{python3_pkgversion}dist(importlib-metadata)) = 6
Provides: bundled(python%{python3_pkgversion}dist(importlib-resources)) = 5.10.2
Provides: bundled(python%{python3_pkgversion}dist(jaraco-text)) = 3.7
Provides: bundled(python%{python3_pkgversion}dist(more-itertools)) = 8.8
Provides: bundled(python%{python3_pkgversion}dist(ordered-set)) = 3.1.1
Provides: bundled(python%{python3_pkgversion}dist(packaging)) = 23.1
Provides: bundled(python%{python3_pkgversion}dist(typing-extensions)) = 4.4
Provides: bundled(python%{python3_pkgversion}dist(typing-extensions)) = 4.0.1
Provides: bundled(python%{python3_pkgversion}dist(zipp)) = 3.7
Provides: bundled(python%{python3_pkgversion}dist(tomli)) = 2.0.1
}

%{bundled}

# For users who might see ModuleNotFoundError: No module named 'pkg_resoureces'
# NB: Those are two different provides: one contains underscore, the other hyphen
%py_provides    python%{python3_pkgversion}-pkg_resources
%py_provides    python%{python3_pkgversion}-pkg-resources

%description
Setuptools is a collection of enhancements to the Python 3 distutils that allow
you to more easily build and distribute Python 3 packages, especially ones that
have dependencies on other packages.

This package also contains the runtime components of setuptools, necessary to
execute the software that requires pkg_resources.

%if %{without bootstrap}
%package -n     %{python_wheel_pkg_prefix}-%{srcname}-wheel
Summary:        The setuptools wheel
%{bundled}

%description -n %{python_wheel_pkg_prefix}-%{srcname}-wheel
A Python wheel of setuptools to use with venv.
%endif


%prep
%autosetup -p1 -n %{srcname}-%{version}
%if %{without bootstrap}
# If we don't have setuptools installed yet, we use the pre-generated .egg-info
# See https://github.com/pypa/setuptools/pull/2543
# And https://github.com/pypa/setuptools/issues/2550
# WARNING: We cannot remove this folder since Python 3.11.1,
#          see https://github.com/pypa/setuptools/issues/3761
#rm -r %%{srcname}.egg-info
%endif

# Strip shbang
find setuptools pkg_resources -name \*.py | xargs sed -i -e '1 {/^#!\//d}'
# Remove bundled exes
rm -f setuptools/*.exe
# Don't ship these
rm -r docs/conf.py


%build
%if %{with bootstrap}
%py3_build
%else
%py3_build_wheel
%endif

%install
%if %{with bootstrap}
# The setup.py install command tries to import distutils
# but the distutils-precedence.pth file is not yet respected
# and Python 3.12+ no longer has distutils in the standard library.
ln -s setuptools/_distutils distutils
PYTHONPATH=$PWD %py3_install
unlink distutils
%else
%py3_install_wheel %{python_wheel_name}
%endif

# https://github.com/pypa/setuptools/issues/2709
rm -rf %{buildroot}%{python3_sitelib}/pkg_resources/tests/

%if %{without bootstrap}
# Install the wheel for the python-setuptools-wheel package
mkdir -p %{buildroot}%{python_wheel_dir}
install -p dist/%{python_wheel_name} -t %{buildroot}%{python_wheel_dir}
%endif


%check

# Regression tests

%if 0%{?rhel} >= 9
# The test cannot run on RHEL8 due to the test script missing from RPM.
# Verify bundled provides are up to date

cat */_vendor/vendored.txt > vendored.txt
%{_rpmconfigdir}/pythonbundles.py vendored.txt --namespace 'python%{python3_pkgversion}dist' --compare-with '%{bundled}'
%endif

# Regression test, the tests are not supposed to be installed
test ! -d %{buildroot}%{python3_sitelib}/pkg_resources/tests
test ! -d %{buildroot}%{python3_sitelib}/setuptools/tests

%if %{without bootstrap}
# Regression test, the wheel should not be larger than 900 kB
# https://bugzilla.redhat.com/show_bug.cgi?id=1914481#c3
test $(stat --format %%s dist/%{python_wheel_name}) -lt 900000

%py3_check_import setuptools pkg_resources
%endif

# Upstream test suite

%if %{with tests}
# https://github.com/pypa/setuptools/discussions/2607
rm pyproject.toml

# Upstream tests
# --ignore=setuptools/tests/test_integration.py
# --ignore=setuptools/tests/integration/
# --ignore=setuptools/tests/config/test_apply_pyprojecttoml.py
# -k "not test_pip_upgrade_from_source"
#   the tests require internet connection
# --ignore=setuptools/tests/test_editable_install.py
#   the tests require pip-run which we don't have in Fedora
PRE_BUILT_SETUPTOOLS_WHEEL=dist/%{python_wheel_name} \
PYTHONPATH=$(pwd) %pytest \
 --ignore=setuptools/tests/test_integration.py \
 --ignore=setuptools/tests/integration/ \
 --ignore=setuptools/tests/test_editable_install.py \
 --ignore=setuptools/tests/config/test_apply_pyprojecttoml.py \
 --ignore=tools/finalize.py \
 -k "not test_pip_upgrade_from_source and not test_setup_requires_honors_fetch_params"
%endif # with tests


%files -n python%{python3_pkgversion}-setuptools
%license LICENSE
%doc docs/* NEWS.rst README.rst
%{python3_sitelib}/distutils-precedence.pth
%{python3_sitelib}/pkg_resources/
%{python3_sitelib}/setuptools*/
%{python3_sitelib}/_distutils_hack/

%if %{without bootstrap}
%files -n %{python_wheel_pkg_prefix}-%{srcname}-wheel
%license LICENSE
# we own the dir for simplicity
%dir %{python_wheel_dir}/
%{python_wheel_dir}/%{python_wheel_name}
%endif


%changelog
* Tue Jan 23 2024 Miro Hrončok <mhroncok@redhat.com> - 68.2.2-3
- Rebuilt for timestamp .pyc invalidation mode

* Mon Nov 13 2023 Charalampos Stratakis <cstratak@redhat.com> - 68.2.2-2
- Disable bootstrap

* Thu Oct 05 2023 Tomáš Hrnčiar <thrnciar@redhat.com> - 68.2.2-1

- Initial package
- Fedora contributions by:
      Bill Nottingham <notting@fedoraproject.org>
      Charalampos Stratakis <cstratak@redhat.com>
      David Malcolm <dmalcolm@redhat.com>
      Dennis Gilmore <dennis@ausil.us>
      Haikel Guemar <hguemar@fedoraproject.org>
      Ignacio Vazquez-Abrams <ivazquez@fedoraproject.org>
      Jesse Keating <jkeating@fedoraproject.org>
      Karolina Surma <ksurma@redhat.com>
      Kevin Fenzi <kevin@scrye.com>
      Konstantin Ryabitsev <icon@fedoraproject.org>
      Lumir Balhar <lbalhar@redhat.com>
      Matej Stuchlik <mstuchli@redhat.com>
      Michal Cyprian <mcyprian@redhat.com>
      Miro Hrončok <miro@hroncok.cz>
      Nils Philippsen <nils@redhat.com>
      Orion Poplawski <orion@cora.nwra.com>
      Petr Viktorin <pviktori@redhat.com>
      Pierre-Yves Chibon <pingou@pingoured.fr>
      Ralph Bean <rbean@redhat.com>
      Randy Barlow <randy@electronsweatshop.com>
      Robert Kuska <rkuska@redhat.com>
      Thomas Spura <thomas.spura@gmail.com>
      Tomáš Hrnčiar <thrnciar@redhat.com>
      Tomas Orsava <torsava@redhat.com>
      Tomas Radej <tradej@redhat.com>
      Toshio Kuratomi <toshio@fedoraproject.org>
      Troy Dawson <tdawson@redhat.com>
      Ville Skyttä <scop@fedoraproject.org>


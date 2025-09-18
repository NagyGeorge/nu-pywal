# Maintainer: George Nagy <george.nagy0969@gmail.com>

_pyname=nu-pywal
pkgname=python-${_pyname}
pkgver=0.9.1
pkgrel=1
pkgdesc="Generate and change color-schemes on the fly (modernized fork of pywal)"
arch=('any')
url="https://github.com/NagyGeorge/nu-pywal"
license=('MIT')
depends=(
    'imagemagick'
    'python'
)
makedepends=(
    'python-build'
    'python-installer'
    'python-wheel'
    'python-setuptools'
)
optdepends=(
    'feh: for setting wallpaper'
    'nitrogen: for setting wallpaper'
    'python-colorthief: for additional color backends'
    'python-colorama: for colored terminal output'
    'python-send2trash: for safe file deletion'
)
source=("${_pyname}-${pkgver}.tar.gz::https://files.pythonhosted.org/packages/source/${_pyname::1}/${_pyname}/nu_pywal-${pkgver}.tar.gz")
sha256sums=('fe1d711ab5cbd38837022594a3ab9905cce0132cf978737c7a3dc33dbe739a31')

build() {
    cd "nu_pywal-${pkgver}"
    python -m build --wheel --no-isolation
}

package() {
    cd "nu_pywal-${pkgver}"
    python -m installer --destdir="${pkgdir}" dist/*.whl
}

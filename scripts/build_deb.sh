#!/usr/bin/env bash
set -euo pipefail

PACKAGE_NAME="smart-sniper-czu"
PACKAGE_VERSION="${1:-${PACKAGE_VERSION:-0.1.0}}"
PACKAGE_ARCH="all"

ROOT_DIR="$(pwd)"
BUILD_DIR="${ROOT_DIR}/build/deb"
STAGE_DIR="${BUILD_DIR}/${PACKAGE_NAME}_${PACKAGE_VERSION}_${PACKAGE_ARCH}"
INSTALL_DIR="${STAGE_DIR}/opt/${PACKAGE_NAME}"
DEBIAN_DIR="${STAGE_DIR}/DEBIAN"
BIN_DIR="${STAGE_DIR}/usr/bin"
APPS_DIR="${STAGE_DIR}/usr/share/applications"

rm -rf "${STAGE_DIR}"
mkdir -p "${INSTALL_DIR}" "${DEBIAN_DIR}" "${BIN_DIR}" "${APPS_DIR}"

cp "${ROOT_DIR}/main.py" "${INSTALL_DIR}/main.py"
cp "${ROOT_DIR}/uis_sniper_gui.py" "${INSTALL_DIR}/uis_sniper_gui.py"
cp "${ROOT_DIR}/requirements.txt" "${INSTALL_DIR}/requirements.txt"
cp "${ROOT_DIR}/README.md" "${INSTALL_DIR}/README.md"
cp -r "${ROOT_DIR}/smart_sniper" "${INSTALL_DIR}/smart_sniper"
cp "${ROOT_DIR}/resources/smart-sniper-czu.desktop" "${APPS_DIR}/smart-sniper-czu.desktop"

cat > "${DEBIAN_DIR}/control" <<EOF
Package: ${PACKAGE_NAME}
Version: ${PACKAGE_VERSION}
Section: utils
Priority: optional
Architecture: ${PACKAGE_ARCH}
Depends: python3, python3-pip, python3-venv, python3-tk
Maintainer: Smart Sniper Maintainers <maintainers@example.com>
Description: Smart Sniper CZU automation launcher
 Desktop utility for UIS and Moodle monitoring and booking flows.
EOF

cat > "${DEBIAN_DIR}/postinst" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/smart-sniper-czu"
VENV_DIR="${APP_DIR}/.venv"

if [ ! -d "${VENV_DIR}" ]; then
  python3 -m venv "${VENV_DIR}"
fi

"${VENV_DIR}/bin/pip" install --upgrade pip
"${VENV_DIR}/bin/pip" install -r "${APP_DIR}/requirements.txt"
EOF

cat > "${BIN_DIR}/smart-sniper-czu" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/smart-sniper-czu"
VENV_PY="${APP_DIR}/.venv/bin/python"

if [ ! -x "${VENV_PY}" ]; then
  echo "Smart Sniper environment is not initialized. Reinstall package." >&2
  exit 1
fi

exec "${VENV_PY}" "${APP_DIR}/main.py" "$@"
EOF

chmod 0755 "${DEBIAN_DIR}/postinst"
chmod 0755 "${BIN_DIR}/smart-sniper-czu"
chmod 0644 "${APPS_DIR}/smart-sniper-czu.desktop"

dpkg-deb --root-owner-group --build "${STAGE_DIR}" "${BUILD_DIR}/${PACKAGE_NAME}_${PACKAGE_VERSION}_${PACKAGE_ARCH}.deb"
echo "Built package: ${BUILD_DIR}/${PACKAGE_NAME}_${PACKAGE_VERSION}_${PACKAGE_ARCH}.deb"


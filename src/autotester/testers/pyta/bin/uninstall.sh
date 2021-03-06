#!/usr/bin/env bash

# script starts here
if [[ $# -ne 0 ]]; then
    echo "Usage: $0"
    exit 1
fi

# vars
THISSCRIPT=$(readlink -f "${BASH_SOURCE[0]}")
THISDIR=$(dirname "${THISSCRIPT}")
SPECSDIR=$(readlink -f "${THISDIR}/../specs")

# main
echo "[PYTA-UNINSTALL] The following system packages have not been uninstalled: python3. You may uninstall them if you wish."
rm -f "${SPECSDIR}/.installed"

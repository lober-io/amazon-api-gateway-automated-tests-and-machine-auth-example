#!/bin/bash
cd /opt/
export NVM_DIR="/opt/.nvm"
mkdir $NVM_DIR
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
. $NVM_DIR/nvm.sh
nvm install 16.0.0
cd /opt/book_api/
npm install /opt/book_api
#!/bin/bash

set -e
cd ~
curl https://raw.github.com/mukerjee/cdn/master/id_rsa > id_rsa
chmod 600 id_rsa
mkdir -p .ssh
mv id_rsa .ssh/
#echo "export PATH=\"~/fedora-bin/xia-core/bin:\$PATH\"" > .bash_profile
#echo "alias pl='cd ~/fedora-bin/xia-core/experiments/planetlab/'" >> .bash_profile
mkdir -p cdn
cd cdn
rsync --rsh='ssh -o StrictHostKeyChecking=no -p5556' update@gs11698.sp.cs.cmu.edu:~/cdn/bin-files ./
rsync --rsh='ssh -o StrictHostKeyChecking=no -p5556' -ar --files-from=./bin-files update@gs11698.sp.cs.cmu.edu:~/cdn/ ./

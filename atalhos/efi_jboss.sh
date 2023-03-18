#!/bin/bash
JAVA_HOME="$HOME/trabalho/programas/java/jdk1.8.0_351"
PATH="$JAVA_HOME/bin:$PATH"

pushd $HOME/trabalho/spread/servidores/jboss-eap-6.4-siefi/bin/ && ./standalone.sh

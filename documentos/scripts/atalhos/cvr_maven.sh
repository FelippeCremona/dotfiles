#!/bin/bash

LANG="pt_BR.UTF-8"

BASE_SISTEMA="$HOME/trabalho/caixa/sistemas/sicvr/des/cvr-bnd"
# JAVA_HOME="$HOME/.sdkman/candidates/java/current"
JAVA_HOME="$HOME/trabalho/programas/java/jdk-11.0.17/"
PATH="$JAVA_HOME/bin:$PATH"

SETTINGS_MAVEN="$HOME/trabalho/programas/maven/settings.xml"
PATH="$HOME/trabalho/programas/maven/apache-maven-3.8.6/bin:$PATH"

pushd $BASE_SISTEMA && mvn clean install -Dskiptest --settings $SETTINGS_MAVEN

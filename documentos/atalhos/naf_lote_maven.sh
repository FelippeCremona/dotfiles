#!/bin/bash

BASE_SISTEMA="$HOME/trabalho/caixa/sistemas/sinaf/des/naf-acoes-lote"
BASE_SERVIDOR="$HOME/trabalho/caixa/servidores/jboss-eap-7.1-sinaf-acoes-lote"
CAMINHO_TARGET="$BASE_SISTEMA/ear/target"
PACOTE="acoes-lote.ear"

# SETTINGS_MAVENS="$HOME/trabalho/programas/maven/settings_novo.xml"
SETTINGS_MAVENS="$HOME/.m2/settings.xml"
PATH="$HOME/trabalho/programas/maven/apache-maven-3.8.6/bin:$PATH"

JAVA_HOME="$HOME/trabalho/programas/java/jdk1.8.0_351"
PATH="$JAVA_HOME/bin:$PATH"

rm -R $CAMINHO_TARGET

rm -R $BASE_SERVIDOR/standalone/deployments
mkdir $BASE_SERVIDOR/standalone/deployments

# pushd $BASE_SISTEMA && mvn dependency:go-offline
pushd $BASE_SISTEMA && mvn install -DskipTests --settings $SETTINGS_MAVENS
# pushd $BASE_SISTEMA && mvn dependency:resolve --settings $BASE_REPOSITORIO/settings.xml
# pushd $BASE_SISTEMA && mvn dependency:go-offline && mvn clean install -o -DskipTests --settings $BASE_REPOSITORIO/settings.xml

cp $CAMINHO_TARGET/$PACOTE $BASE_SERVIDOR/standalone/deployments/

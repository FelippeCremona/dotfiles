#!/bin/bash

BASE_SISTEMA="$HOME/trabalho/spread/sistemas/siefi/des/SIEFI"
BASE_SERVIDOR="$HOME/trabalho/spread/servidores/jboss-eap-6.4-siefi"
CAMINHO_TARGET="$BASE_SISTEMA/siefi-ear/target"
PACOTE="siefi-ear.ear"

SETTINGS_MAVEN="$HOME/trabalho/programas/maven/settings_antigo.xml"
PATH="$HOME/trabalho/programas/maven/apache-maven-3.8.6/bin:$PATH"
#JAVA_HOME="$HOME/.sdkman/candidates/java/current"
JAVA_HOME="$HOME/trabalho/programas/java/jdk1.8.0_351"
PATH="$JAVA_HOME/bin:$PATH"

OPT="$HOME/trabalho/programas/jar/ojdbc6.jar"
#java -version
#mvn -v

rm -R $CAMINHO_TARGET

rm -R $BASE_SERVIDOR/standalone/deployments
mkdir $BASE_SERVIDOR/standalone/deployments

cp $OPT $BASE_SERVIDOR/standalone/deployments/

#pushd $BASE_SISTEMA && mvn dependency:resolve --settings $BASE_REPOSITORIO/settings.xml
pushd $BASE_SISTEMA && mvn clean install -DskipTests --settings $SETTINGS_MAVEN
#pushd $BASE_SISTEMA && $HOME/trabalho/programas/maven/apache-maven-3.8.6/bin/mvn clean install -DskipTests --settings $BASE_REPOSITORIO/settings.xml
cp $CAMINHO_TARGET/$PACOTE $BASE_SERVIDOR/standalone/deployments/

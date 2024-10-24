#!/bin/bash

BASE_SISTEMA="$HOME/trabalho/caixa/sistemas/sigip/des/gip"
BASE_SERVIDOR="$HOME/trabalho/caixa/servidores/jboss-eap-7.1-sigip"
CAMINHO_TARGET="$BASE_SISTEMA/sigip-ear/target"
PACOTE="sigip.ear"

SETTINGS_MAVEN="$HOME/trabalho/programas/maven/settings_padrao.xml"
PATH="$HOME/trabalho/programas/maven/apache-maven-3.8.8/bin:$PATH"
#JAVA_HOME="$HOME/.sdkman/candidates/java/current"
JAVA_HOME="$HOME/trabalho/programas/java/jdk1.8.0_351"
PATH="$JAVA_HOME/bin:$PATH"

# OPT="$HOME/trabalho/programas/jar/ojdbc6.jar"
#java -version
#mvn -v

rm -R $CAMINHO_TARGET

rm -R $BASE_SERVIDOR/standalone/deployments
mkdir $BASE_SERVIDOR/standalone/deployments

# cp $OPT $BASE_SERVIDOR/standalone/deployments/

#pushd $BASE_SISTEMA && mvn dependency:resolve --settings $BASE_REPOSITORIO/settings.xml
pushd $BASE_SISTEMA && mvn clean install -DskipTests --settings $SETTINGS_MAVEN
#pushd $BASE_SISTEMA && $HOME/trabalho/programas/maven/apache-maven-3.8.6/bin/mvn clean install -DskipTests --settings $BASE_REPOSITORIO/settings.xml
cp $CAMINHO_TARGET/$PACOTE $BASE_SERVIDOR/standalone/deployments/

#!/bin/bash

# Diretório do sistemas
BASE_SISTEMA="$HOME/trabalho/pessoal/envia-email"

# JAVA
# JAVA_HOME="$HOME/trabalho/programas/java/jdk-11.0.17"
JAVA_HOME="$HOME/trabalho/programas/java/jdk-17.0.5"
PATH="$JAVA_HOME/bin:$PATH"

# Variaveis do MAVEN
PATH="$HOME/trabalho/programas/maven/apache-maven-3.8.6/bin:$PATH"
SETTINGS_MAVEN="$HOME/.m2/settings.xml"
M2_HOME="$HOME/trabalho/programas/maven/apache-maven-3.8.6"
PATH="$M2_HOME/bin:$PATH"

pushd $BASE_SISTEMA && mvn quarkus:dev --settings $SETTINGS_MAVEN

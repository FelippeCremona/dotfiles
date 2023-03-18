#!/bin/bash

# Diretório do sistemas
BASE_SISTEMA="$HOME/trabalho/spread/sistemas/empresa"

# JAVA
JAVA_HOME="$HOME/trabalho/programas/java/jdk-11.0.17"
PATH="$JAVA_HOME/bin:$PATH"

# Variaveis do MAVEN
PATH="$HOME/trabalho/programas/maven/apache-maven-3.8.6/bin:$PATH"
SETTINGS_MAVEN="$HOME/trabalho/programas/maven/settings_novo.xml"
M2_HOME="$HOME/trabalho/programas/maven/apache-maven-3.8.6"
PATH="$M2_HOME/bin:$PATH"

pushd $BASE_SISTEMA && mvn quarkus:dev --settings $SETTINGS_MAVEN

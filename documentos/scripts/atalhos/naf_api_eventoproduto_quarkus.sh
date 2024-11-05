#!/bin/bash

# Diretório do sistemas
BASE_SISTEMA="$HOME/trabalho/caixa/sistemas/sinaf/des/naf-api-eventoproduto"

# JAVA
JAVA_HOME="$HOME/trabalho/programas/java/jdk-11.0.17"
PATH="$JAVA_HOME/bin:$PATH"

# Variaveis do MAVEN
PATH="$HOME/trabalho/programas/maven/apache-maven-3.8.6/bin:$PATH"
SETTINGS_MAVEN="$HOME/trabalho/programas/maven/settings.xml"
M2_HOME="$HOME/trabalho/programas/maven/apache-maven-3.8.6"
PATH="$M2_HOME/bin:$PATH"

# Variaveis do SISTEMA
export DATASOURCE_JDBC_URL=jdbc:db2://172.16.160.61:5021/CSD1
export DATASOURCE_USERNAME=SNAFBD01
export PUBLICKEY=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAzcYY/UbvrEldbQRd4TgLeP9bS8YnaL67MZUsfozWRyocBF3S0L7UEbkPaPoCoBnhoRv8VJHp0grqe3mqEmkMuDlt20Vx6q04ADDyS0c8xaU+Ot+g1Pgwjze944ATUjZogEMko6jvqqUGTt/Nt64yCCIaMaTB119vOBExQim7vPHNe/o7hLxh6VBYINxFA/esxjz8j28/uJWIiK0Gvt07Yx7ycn2DJlQHjnH2GzCSUL87AAYmjyYxW2JZaPLLvRlpcHIWrlr9GNtLiq0++xfJ0jFYxQWs1jxhlfXdqr8NE5vfA/RRRjRFnWzFOhIsOnIHPO9eEwwYzCZSoW2zXkFDYwIDAQAB
export SSOINTER_ISSUER=https://login.des.caixa/auth/realms/intranet

pushd $BASE_SISTEMA && mvn quarkus:dev --settings $SETTINGS_MAVEN

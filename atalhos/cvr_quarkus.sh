#!/bin/bash

# Diretório do sistemas
BASE_SISTEMA="$HOME/trabalho/spread/sistemas/sicvr/des/cvr-bnd"

# JAVA
# JAVA_HOME="$HOME/.sdkman/candidates/java/current"
JAVA_HOME="$HOME/trabalho/programas/java/jdk-11.0.17"
PATH="$JAVA_HOME/bin:$PATH"

# Variaveis do MAVEN
PATH="$HOME/trabalho/programas/maven/apache-maven-3.8.6/bin:$PATH"
SETTINGS_MAVEN="$HOME/trabalho/programas/maven/settings_novo.xml"
M2_HOME="$HOME/trabalho/programas/maven/apache-maven-3.8.6"
PATH="$M2_HOME/bin:$PATH"

# Variaveis do SISTEMA
# env SICVR.SSO.URL=https://login.des.caixa/auth
# env SICVR.STORAGE=$HOME/trabalho/spread/armazenamento
# env SICVR.AMBIENTE=DES
# env SICVR.DATASOURCE.USERNAME=SCVRBD01
# env SICVR.DATASOURCE.PASSWORD=pwscvrbd01
# env SICVR.DATASOURCE.JDBC.URL=jdbc:oracle:thin:@cnpexdadvm01-scan4.extra.caixa.gov.br:1521/orad01ng

export SSO_URL=https://login.des.caixa/auth
export STORAGE=$HOME/trabalho/spread/armazenamento
export AMBIENTE=DES
export DATASOURCE_USERNAME=SCVRBD01
export DATASOURCE_PASSWORD=pwscvrbd01
export DATASOURCE_JDBC_URL=jdbc:oracle:thin:@172.16.140.243:1521/orad01ng

# export API_SIICO_URL=https://portalapi-rest-dev.nprd2.caixa/informacoes-corporativas-
export API_SIICO_URL=https://api.des.caixa:8443/informacoes-corporativas-
export API_KEY_SIICO=l7e62cd9835b404e619129dcf7ad97d30d
# export API_SICLI_URL=http://apicadastro.des.caixa/cadastro/ws
export API_SICLI_URL=https://api.des.caixa:8443/cadastro

pushd $BASE_SISTEMA && mvn quarkus:dev --settings $SETTINGS_MAVEN

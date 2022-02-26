# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

###########################################################
# Dockerfile to build pySTeVe container images
# Based on Debian
############################################################

# Set base images
FROM debian

MAINTAINER Daniel Gruno

# Update aptitude repo data
RUN apt-get update

# Install base packages
RUN apt-get install -y apache2 subversion python3-pip wget
RUN pip install elasticsearch


# Download pySTeVe
RUN svn co https://svn.apache.org/repos/asf/steve/trunk/pysteve/ /var/www/steve

# Copy libs
RUN cp -R /var/www/steve/lib /var/www/steve/www/cgi-bin/lib


# Add httpd config
RUN rm /etc/apache2/sites-enabled/*.conf
ADD https://svn.apache.org/repos/asf/steve/trunk/pysteve/httpd.conf /etc/apache2/sites-enabled/000-default.conf

# Install & Start ElasticSearch
RUN wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | apt-key add -
RUN apt-get install -y apt-transport-https
RUN echo "deb https://artifacts.elastic.co/packages/7.x/apt stable main" | tee -a /etc/apt/sources.list.d/elastic-7.x.list
RUN apt-get update && apt-get -y install elasticsearch

EXPOSE 9200 9300
RUN service elasticsearch start && sleep 30 && service elasticsearch status

# Enable mod_cgi
RUN a2enmod cgi

# Expose port for httpd
EXPOSE 80

# Set default container startup sequence
ENTRYPOINT service elasticsearch start && service apache2 start && bash

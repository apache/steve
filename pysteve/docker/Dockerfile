############################################################
# Dockerfile to build pySTeVe container images
# Based on Debian
############################################################

# Set base images
FROM debian
FROM elasticsearch

MAINTAINER Daniel Gruno

# Update aptitude repo data
RUN apt-get update

# Install base packages
RUN apt-get install -y apache2 subversion python-pip
RUN pip install elasticsearch


# Download pySTeVe
RUN svn co https://svn.apache.org/repos/asf/steve/trunk/pysteve/ /var/www/steve

# Copy libs
RUN cp -R /var/www/steve/lib /var/www/steve/www/cgi-bin/lib


# Add httpd config
RUN rm /etc/apache2/sites-enabled/*.conf
ADD https://svn.apache.org/repos/asf/steve/trunk/pysteve/httpd.conf /etc/apache2/sites-enabled/000-default.conf


# Start ElasticSearch
EXPOSE 9200 9300
RUN service elasticsearch start && sleep 30 && service elasticsearch status

# Enable mod_cgi
RUN a2enmod cgi

# Expose port for httpd
EXPOSE 80

# Set default container startup sequence
ENTRYPOINT service elasticsearch start && service apache2 start && bash

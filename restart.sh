ps auxww | grep 'celery worker' | awk '{print $2}' | xargs sudo kill -9
sudo -u mongodb mongod --shutdown --dbpath /var/lib/mongodb/
sudo -u mongodb mongod --fork --dbpath /var/lib/mongodb/ --logpath /var/log/mongodb/mongod.log &
sudo -u celery celery worker -A tryit -l WARNING -f /var/log/celery/celery.log &

sudo chmod 777 /var/run/docker.sock
docker cp ./async_hls_file_watcher.py 918979960c2c:/mnt
docker cp ./.env 918979960c2c:/mnt
docker cp ./requirements.txt 918979960c2c:/mnt
docker exec 918979960c2c apt-get update
docker exec 918979960c2c apt-get install -y pip
docker exec 918979960c2c pip install -r ./mnt/requirements.txt
docker exec 918979960c2c mkdir -p ./mnt/hls
docker exec -it 918979960c2c bin/sh
cd mnt
python3 async_hls_file_watcher.py
import os
import asyncio
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import b2sdk.v2 as b2
from dotenv import load_dotenv
import re
import glob

load_dotenv()

info = b2.InMemoryAccountInfo()
b2_api = b2.B2Api(info)
b2_api.authorize_account("production", os.getenv("B2_KEY_ID"), os.getenv("B2_APPLICATION_KEY"))
b2_bucket = b2_api.get_bucket_by_name("coinsniper-api-test")

class AsyncHLSFileWatcher(FileSystemEventHandler):
    def __init__(self, directory_to_watch, num_workers=6, stream_timeout=180):
        self.directory_to_watch = directory_to_watch
        self.upload_queue = asyncio.Queue()
        self.last_update_time = {}
        self.num_workers = num_workers
        self.m3u8_files = {}
        self.stream_timeout = stream_timeout  # 180 seconds by default

    def on_any_event(self, event):
        if event.is_directory:
            return
        
        if event.event_type in ['created', 'modified', 'moved'] and 'rtmp-stream-01' not in event.src_path:
            file_path = event.dest_path if (event.event_type == 'moved' or event.event_type == 'modified') else event.src_path

            if file_path.endswith('.m3u8'):
                print(f"M3U8 file event detected: {event.event_type} - {file_path}")
                if 'index' not in os.path.basename(file_path).lower():
                    asyncio.run(self.upload_queue.put(file_path))
                    print(f"Non-index M3U8 file queued for direct upload: {file_path}")
                else:
                    asyncio.run(self.process_m3u8(file_path))

    async def process_m3u8(self, m3u8_path):
        await asyncio.sleep(0.5)  # Short delay to ensure file writing is complete
        if m3u8_path not in self.m3u8_files:
            self.m3u8_files[m3u8_path] = set()
            print(f"New M3U8 file detected: {m3u8_path}")
        
        await self.check_m3u8_updates(m3u8_path)

    async def check_m3u8_updates(self, m3u8_path):
        try:
            with open(m3u8_path, 'r') as file:
                content = file.read()
            
            current_ts_files = set(line.strip() for line in content.splitlines() if line.strip().endswith('.ts'))
            new_ts_files = current_ts_files - self.m3u8_files.get(m3u8_path, set())
            
            if new_ts_files:
                print(f"New TS files in {m3u8_path}: {', '.join(new_ts_files)}")
                for ts_file in new_ts_files:
                    ts_path = os.path.join(os.path.dirname(m3u8_path), ts_file)
                    if os.path.exists(ts_path):
                        await self.upload_queue.put(ts_path)
                        print(f"Queued for upload: {ts_path}")
                    else:
                        print(f"Warning: TS file {ts_file} not found in directory.")
                await self.upload_queue.put(m3u8_path)
                print(f"Queued for upload: {m3u8_path}")
                self.m3u8_files[m3u8_path].update(new_ts_files)
                self.last_update_time[m3u8_path] = time.time()
        except Exception as e:
            print(f"Error processing {m3u8_path}: {str(e)}")

    async def check_stream_end(self):
        while True:
            current_time = time.time()
            ended_streams = []

            for m3u8_path, last_update in self.last_update_time.items():
                # Only consider m3u8 files that have "index" in their path
                if "index" in m3u8_path and current_time - last_update > self.stream_timeout:
                    print(f"Stream seems to have ended for {m3u8_path}")
                    ended_streams.append(m3u8_path)
            
            for ended_stream in ended_streams:
                # Get the base directory of the ended stream
                base_dir = os.path.dirname(os.path.dirname(ended_stream))
                
                # Find all index.m3u8 files in subdirectories
                for resolution_m3u8 in glob.glob(os.path.join(base_dir, "*", "index.m3u8")):
                    print(f"Converting to VOD: {resolution_m3u8}")
                    await self.convert_to_vod(resolution_m3u8)
                
                # Convert the main m3u8 file
                main_m3u8 = os.path.join(base_dir, os.path.basename(base_dir) + ".m3u8")
                if os.path.exists(main_m3u8):
                    print(f"Converting main playlist to VOD: {main_m3u8}")
                    await self.convert_to_vod(main_m3u8)
                
                # Remove the ended stream from tracking
                self.last_update_time.pop(ended_stream)
            
            await asyncio.sleep(60)  # Check every minute

    async def convert_to_vod(self, m3u8_path):
        try:
            with open(m3u8_path, 'r') as file:
                content = file.read()

            # Remove live-specific tags
            content = re.sub(r'#EXT-X-ENDLIST.*\n?', '', content)
            content = re.sub(r'#EXT-X-PLAYLIST-TYPE:EVENT.*\n?', '', content)

            # Add VOD-specific tags
            content = "#EXT-X-PLAYLIST-TYPE:VOD\n" + content

            # Ensure all segments are included (remove any #EXT-X-DISCONTINUITY tags)
            content = re.sub(r'#EXT-X-DISCONTINUITY.*\n?', '', content)

            # Add the ENDLIST tag at the end
            content += "\n#EXT-X-ENDLIST\n"

            print(f"Converted {m3u8_path} to VOD format")

            # Queue the modified content for upload
            file_name = os.path.relpath(m3u8_path, self.directory_to_watch)
            await self.upload_queue.put((file_name, content.encode('utf-8'), 'application/vnd.apple.mpegurl'))

            print(f"Queued converted VOD content for upload: {file_name}")
        except Exception as e:
            print(f"Error converting {m3u8_path} to VOD: {str(e)}")

    async def upload_worker(self):
        while True:
            file_path = await self.upload_queue.get()
            file_path = file_path.replace('\\', '/')

            start_time = time.time()
            try:
                content_type = 'application/vnd.apple.mpegurl' if file_path.endswith('.m3u8') else 'video/MP2T'
                uploaded_file = await asyncio.to_thread(
                    b2_bucket.upload_local_file,
                    local_file=file_path,
                    file_name=os.path.relpath(file_path, self.directory_to_watch),
                    file_infos={'ContentType': content_type},
                )

                end_time = time.time()
                upload_duration = end_time - start_time
                
                file_size = os.path.getsize(file_path)
                upload_speed = file_size / upload_duration / 1024 / 1024  # in MB/s

                print(f"Uploaded {file_path} to B2 bucket")
                print(f"Upload time: {upload_duration:.2f} seconds")
                print(f"File size: {file_size / 1024 / 1024:.2f} MB")
                print(f"Upload speed: {upload_speed:.2f} MB/s")
                print(f"-------------------------------------")
            except Exception as e:
                print(f"Failed to upload {file_path}: {str(e)}")
            finally:
                self.upload_queue.task_done()

    async def run(self):
        observer = Observer()
        observer.schedule(self, self.directory_to_watch, recursive=True)
        observer.start()
        print(f"Watching directory: {self.directory_to_watch}")

        self.upload_workers = [asyncio.create_task(self.upload_worker()) for _ in range(self.num_workers)]
        print(f"Started {self.num_workers} upload workers")

        # Create the stream end checker task
        stream_end_checker = asyncio.create_task(self.check_stream_end())
        print("Started stream end checker")

        try:
            # Keep the main task running
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            print("Cancelling all tasks...")
            for worker in self.upload_workers:
                worker.cancel()
            observer.stop()
        finally:
            # Wait for all tasks to complete
            all_tasks = self.upload_workers + [stream_end_checker]
            await asyncio.gather(*all_tasks, return_exceptions=True)
            observer.join()
            print("All tasks have been cancelled and observer stopped.")

if __name__ == "__main__":
    directory_to_watch = "./hls"  # Update this to your HLS directory path
    watcher = AsyncHLSFileWatcher(directory_to_watch)
    asyncio.run(watcher.run())

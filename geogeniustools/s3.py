import os

from geogeniustools.rda.env_variable import USER_ENDPOINT
from obs import ObsClient
from tqdm import tqdm

from geogeniustools.auth import Auth
from geogeniustools.rda.error import AkSkNotFound


class S3(object):

    def __init__(self, **kwargs):
        self.interface = Auth(**kwargs)

        # store a ref to the geogenius connection
        self.geogenius_connection = self.interface.geogenius_connection

        # store a ref to the logger
        self.logger = self.interface.logger

        self._info = None
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = ObsClient(
                access_key_id=self.info['S3_access_key'],
                secret_access_key=self.info['S3_secret_key'],
                server=self.info['endpoint']
            )
        return self._client

    @property
    def info(self):
        if not self._info:
            self._info = self._load_info()
        return self._info

    @info.setter
    def info(self, value):
        self._info = value

    def _load_info(self):
        s3_info = {}
        s3_access_key = os.environ.get("ACCESS_KEY", None)
        s3_secret_key = os.environ.get("SECRET_KEY", None)
        if not s3_access_key or not s3_secret_key:
            raise AkSkNotFound("ACCESS_KEY or SECRET_KEY not set in environment")
        s3_info["S3_access_key"] = s3_access_key
        s3_info["S3_secret_key"] = s3_secret_key
        storage_url = '%s/users/storage' % USER_ENDPOINT
        r = self.geogenius_connection.get(storage_url)
        r.raise_for_status()
        s3_info["bucket"] = r.json().get("bucket")
        s3_info["endpoint"] = r.json().get("endpoint")
        return s3_info

    def _parse_obs_path(self, obs_path):
        if obs_path is None or obs_path == "":
            raise Exception('obs_path is invalid')
        if obs_path.startswith("obs://"):
            bucket_with_path = obs_path[6:]
            bucket = bucket_with_path.split("/", 1)[0]
            if bucket != self.info["bucket"]:
                raise Exception("don't have privilege to operate bucket '{}'".format(bucket))
            obs_path = "/" if len(bucket_with_path.split("/", 1)) == 1 else bucket_with_path.split("/", 1)[1]
        return obs_path

    def upload(self, local_file, obs_path, part_size=10 * 1024 * 1024, task_num=5, enable_checkpoint=True):
        """
        Upload files to your obs.

        Args:
            local_file (str): a path to a local file to upload, directory structures are not mirrored
            obs_path: a key (location) on s3 to upload the file to
            part_size: segment size
            task_num: maximum number of concurrent uploads
            enable_checkpoint: turn on breakpoint resume mode

        Returns:
            str: obs path file was saved to

        Examples:
            >>> upload('path/to/image.tif', obs_path='images/image.tif')
            'obs://yourbucket/images/image.tif'

            >>> upload('./path/to/image.tif', obs_path='obs://yourbucket/images/image.tif')
            'obs://yourbucket/images/image.tif'
        """
        if not os.path.exists(local_file):
            raise Exception(local_file + " does not exist.")
        obs_path = self._parse_obs_path(obs_path)
        if obs_path != "" and obs_path[0] == '/':
            obs_path = obs_path[1:]
        bucket = self.info['bucket']
        s3conn = self.client
        with DownloadProgress(unit='B', unit_scale=True, miniters=1, desc="Uploading '%s'" % local_file) as pbar:
            s3conn.uploadFile(bucket, obs_path, local_file, part_size, task_num, enable_checkpoint,
                              progressCallback=pbar.hook)
        return 'obs://{}/{}'.format(bucket, obs_path)

    def delete(self, obs_path):
        """
        Delete content in obs.
        Obs_path can be a directory or a file (e.g., my_dir or my_dir/my_image.tif or obs://yourbucket/mydir)
        If location is a directory, all files in the directory are deleted.
        If it is a file, then that file is deleted.

        Args:
           obs_path (str): obs path. Can be a directory or a file
           (e.g., my_dir or my_dir/my_image.tif or obs://yourbucket/mydir).
        """
        bucket = self.info['bucket']
        s3conn = self.client
        obs_path = self._parse_obs_path(obs_path)
        # remove head and/or trail backslash from obs_path
        if obs_path != "" and obs_path[0] == '/':
            obs_path = obs_path[1:]
        if obs_path != "" and obs_path[-1] == '/':
            obs_path = obs_path[:-2]

        max_keys = 100
        marker = None
        while True:
            resp = s3conn.listObjects(bucketName=bucket, prefix=obs_path,
                                      max_keys=max_keys, marker=marker)
            if resp.status < 300:
                for key in resp.body.contents:
                    s3conn.deleteObject(bucketName=bucket, objectKey=key)
                if not resp.body.is_truncated:
                    break
                marker = resp.body.next_marker
            else:
                self.logger.error('errorCode:', resp.errorCode)
                self.logger.error('errorMessage:', resp.errorMessage)
                break

    def download(self, obs_path, local_dir='.'):
        """
        Download content from obs.
        Obs_path can be a directory or a file (e.g., my_dir or my_dir/my_image.tif or obs://yourbucket/mydir)
        If location is a directory, all files in the directory are
        downloaded. If it is a file, then that file is downloaded.

        Args:
           obs_path (str): Obs location.
           local_dir (str): Local directory where file(s) will be stored. Default is here.
        """
        bucket = self.info['bucket']
        s3conn = self.client
        obs_path = self._parse_obs_path(obs_path)
        # remove head and/or trail backslash from obs_path
        obs_path = obs_path.strip('/')
        max_keys = 100
        marker = None
        first = True
        while True:
            resp = s3conn.listObjects(bucketName=bucket, prefix=obs_path, max_keys=max_keys, marker=marker)
            if resp.status < 300:
                if first and len(resp.body.contents) == 0:
                    raise ValueError('Download target {}/{} was not found or inaccessible.'.format(bucket, obs_path))
                for key in resp.body.contents:
                    key = key.key
                    if key.endswith('/'):
                        continue
                    local_path = self._get_download_path(obs_path=obs_path, key=key, local_dir=local_dir)
                    with DownloadProgress(unit='B', unit_scale=True, miniters=1, desc="Downloading 'obs://{}/{}'".format(bucket, key)) as pbar:
                        s3conn.getObject(bucketName=bucket, objectKey=key, downloadPath=local_path, progressCallback=pbar.hook)

                if not resp.body.is_truncated:
                    break
                marker = resp.body.next_marker
                first = False
            else:
                self.logger.error('errorCode:', resp.errorCode)
                self.logger.error('errorMessage:', resp.errorMessage)
                break
        self.logger.debug('Done!')

    def _get_download_path(self, obs_path, key, local_dir):
        # get path to each file
        filepath = key.replace(obs_path, '', 1).lstrip('/')
        filename = key.split('/')[-1]

        file_dir = filepath.split('/')[:-1]
        file_dir = '/'.join(file_dir)
        full_dir = os.path.join(local_dir, file_dir)

        # make sure directory exists
        if not os.path.isdir(full_dir):
            os.makedirs(full_dir)
        return os.path.join(full_dir, filename)

    def list(self, obs_path):
        bucket = self.info['bucket']

        self.logger.debug('Connecting to S3')
        s3conn = self.client

        obs_path = self._parse_obs_path(obs_path)
        # remove head and/or trail backslash from obs_path
        if obs_path != "" and obs_path[0] == '/':
            obs_path = obs_path[1:]
        if obs_path != "" and obs_path[-1] == '/':
            obs_path = obs_path[:-2]

        max_keys = 100
        marker = None
        while True:
            resp = s3conn.listObjects(bucketName=bucket, prefix=obs_path,
                                      max_keys=max_keys, marker=marker)
            if resp.status < 300:
                for key in resp.body.contents:
                    print("obs://{}/{}".format(bucket, key.key))
                if not resp.body.is_truncated:
                    break
                marker = resp.body.next_marker
            else:
                self.logger.error('errorCode:', resp.errorCode)
                self.logger.error('errorMessage:', resp.errorMessage)
                break
        self.logger.debug('Done!')


class DownloadProgress(tqdm):
    already_transferred = 0

    def hook(self, transferred_amount=1, total_amount=1, totalSeconds=None):
        self.total = total_amount
        self.update(transferred_amount - self.already_transferred)
        self.already_transferred = transferred_amount

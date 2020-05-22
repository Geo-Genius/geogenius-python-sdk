#!/bin/bash
set -e
 
MOUNT_OBS_BUCKET=$1
MOUNT_OBS_PREFIX=$2
MOUNT_POINT=$3
 
NB_DIR='/home/jovyan'
 
if [ -z "${MOUNT_OBS_BUCKET}" ]; then
  echo "Data bucket should be set in env parameters to mount obs."
  exit 1
fi
 
if [ -z "${MOUNT_OBS_PREFIX}" ]; then
  echo "Data obs prefix should be set in env parameters to mount obs."
  exit 1
fi
 
if [ -z "${MOUNT_POINT}" ]; then
  echo "mount point should be set in env parameters to mount obs."
  exit 1
fi
 
if [ -z "${ACCESS_KEY_ID}" ]; then
  echo "access key id should be set in env parameters to mount obs."
  exit 1
fi
 
if [ -z "${SECRET_ACCESS_KEY}" ]; then
  echo "secret access key should be set in env parameters to mount obs."
  exit 1
fi
 
if [ -z "${SERVER_URL}" ]; then
  echo "obs server url should be set in env parameters to mount obs."
  exit 1
fi
 
if [ -z "${REGION_NAME}" ]; then
  echo "region name should be set in env parameters to mount obs."
  exit 1
fi
 
HTTP_OBS_URL="http://${SERVER_URL}"
 
mkdir -p ${NB_DIR}
 
MOUNT_PATH="${NB_DIR}/${MOUNT_POINT}"
 
mkdir -p ${MOUNT_PATH}
 
echo ${ACCESS_KEY_ID}:${SECRET_ACCESS_KEY} > ~/.passwd-s3fs
chmod 600 ~/.passwd-s3fs
 
s3fs ${MOUNT_OBS_BUCKET}:/${MOUNT_OBS_PREFIX} ${MOUNT_PATH} -o url=${HTTP_OBS_URL} -o endpoint=${REGION_NAME}
 
echo "Successful finished mount obs"

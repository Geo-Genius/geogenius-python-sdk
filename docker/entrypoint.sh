#!/bin/bash
# set notebook directory
NB_DIR='/home/jovyan'
mkdir -p ${NB_DIR}
 

 
# mount data and user ouput obs path
sh /usr/local/bin/mount_obs.sh ${DATA_BUCKET} ${DATA_PREFIX} ${DATA_MOUNT_POINT}
 
sh /usr/local/bin/mount_obs.sh ${OUTPUT_BUCKET} ${OUTPUT_PREFIX} ${OUTPUT_MOUNT_POINT}


 # download code
if [ -n "${CODE_OBS_PATH}" ]; then
  cd /opt/obsutil_linux_amd64*

  ./obsutil config -i=${ACCESS_KEY_ID} -k=${SECRET_ACCESS_KEY} -e=${SERVER_URL}

  OBS_UTIL_PREFIX="obs://"

  ./obsutil cp ${OBS_UTIL_PREFIX}${CODE_OBS_PATH} ${NB_DIR}/${OUTPUT_MOUNT_POINT}/${CODE_OBS_PATH##*/}

  # if code is zip file, unzip it
  if [ "${CODE_OBS_PATH##*.}" = "zip" ]; then
    cd ${NB_DIR}/${OUTPUT_MOUNT_POINT}

    unzip ${NB_DIR}/${OUTPUT_MOUNT_POINT}/${CODE_OBS_PATH##*/}

    rm ${NB_DIR}/${OUTPUT_MOUNT_POINT}/${CODE_OBS_PATH##*/}
  fi

  echo "finish download code"
fi

# unset syn_to_path extension
jupyter nbextension disable sync_to_path/main --section='tree'

# install and enable the geogenius_jupyter_notebook_extensions
jupyter nbextension install --py geogenius_jupyter_notebook_extensions --sys-prefix
jupyter nbextension enable geogenius_jupyter_notebook_extensions --py --sys-prefix
set_config "http://${NOTEBOOK_EXTENSION_ENDPOINT}/extensions/notebook"

# start notebook
jupyter notebook \
--notebook-dir=${NB_DIR}/${OUTPUT_MOUNT_POINT} \
--ip=0.0.0.0 \
--no-browser \
--allow-root \
--port=8888 \
--NotebookApp.token='' \
--NotebookApp.password='' \
--NotebookApp.allow_origin='*' \
--NotebookApp.base_url=${NB_PREFIX} \
--NotebookApp.tornado_settings="{\"headers\": {\"Content-Security-Policy\": \"frame-ancestors self localhost:*  *;\"}}"

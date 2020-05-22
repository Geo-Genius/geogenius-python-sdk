FROM swr.cn-north-5.myhuaweicloud.com/geogenius/tensorflow-gpu:v0.7

USER root

COPY sources.list /opt/
COPY mount_obs.sh entrypoint.sh /usr/local/bin/
COPY pip.conf /root/.pip/
ADD geogenius_python_sdk.tar.gz /root/anaconda3/envs

ENV PATH /root/anaconda3/envs/geogenius_python_sdk/bin:$PATH
ENV NOTEBOOK_EXTENSION_ENDPOINT 100.94.14.213:8080

# install zip/unzip/s3fs, download obsutil,
RUN mv /etc/apt/sources.list /etc/apt/sources.list~ && \
    mv /opt/sources.list /etc/apt/sources.list && \
    rm -f /etc/apt/sources.list && \
    rm -rf /var/lib/apt/lists/* && \
    mv /etc/apt/sources.list~ /etc/apt/sources.list && \
    cd /opt/ && \
    wget https://obs-community.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_linux_amd64.tar.gz && \
    tar -xzvf obsutil_linux_amd64.tar.gz && \
    rm obsutil_linux_amd64.tar.gz && \
    cd obsutil_linux_amd64*/ && \
    chmod 755 obsutil && \
    chown root:100 /usr/local/bin/mount_obs.sh && \
    chown root:100 /usr/local/bin/entrypoint.sh && \
    chmod 755 /usr/local/bin/mount_obs.sh && \
    chmod 755 /usr/local/bin/entrypoint.sh

CMD ["entrypoint.sh"]

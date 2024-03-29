FROM update:v6
ADD ./geogenius-python-sdk.tar.gz /opt
ARG MANAGER_ENDPOINT
ARG THUMBNAIL_URL
ARG X_AUTH_TOKEN
ARG PROJECT_ID
ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY
ARG AWS_REGION
ARG AWS_S3_ENDPOINT
ENV MANAGER_ENDPOINT ${MANAGER_ENDPOINT}
ENV THUMBNAIL_URL ${THUMBNAIL_URL}
ENV X_AUTH_TOKEN ${X_AUTH_TOKEN}
ENV PROJECT_ID ${PROJECT_ID}
ENV AWS_ACCESS_KEY_ID ${AWS_ACCESS_KEY_ID}
ENV AWS_SECRET_ACCESS_KEY ${AWS_SECRET_ACCESS_KEY}
ENV AWS_REGION ${AWS_REGION}
ENV AWS_S3_ENDPOINT ${AWS_S3_ENDPOINT}
ENV PATH ${PATH}:/usr/local/bin/anaconda3/bin/
WORKDIR /opt/geogenius-python-sdk
RUN ["/usr/local/bin/anaconda3/bin/python", "setup.py", "install"]

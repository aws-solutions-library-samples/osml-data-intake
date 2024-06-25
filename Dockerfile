# Copyright 2024 Amazon.com, Inc. or its affiliates.

FROM public.ecr.aws/lambda/python:3.11 as osml_data_intake

# Build time arguments
ARG BUILD_CERT=/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem
ARG PIP_INSTALL_LOCATION=https://pypi.org/simple/
ARG MINICONDA_VERSION=Miniconda3-latest-Linux-x86_64
ARG MINICONDA_URL=https://repo.anaconda.com/miniconda/${MINICONDA_VERSION}.sh
ARG CONDA_ENV_NAME="osml_data_intake"

# Define required packages to install
ARG PACKAGES="wget"

# Give sudo permissions
USER root

# Configure, update, and refresh yum enviornment
RUN yum update -y && yum clean all && yum makecache

# Install all our dependancies
RUN yum install -y $PACKAGES

# Install Miniconda
RUN wget -c ${MINICONDA_URL} && \
    chmod +x ${MINICONDA_VERSION}.sh && \
    ./${MINICONDA_VERSION}.sh -b -f -p /opt/conda && \
    rm ${MINICONDA_VERSION}.sh && \
    ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh

# Add conda to the path
ENV PATH=/opt/conda/bin:$PATH

# Copy conda ENV
COPY environment.yml ${LAMBDA_TASK_ROOT}

# Install python with conda
RUN conda env create -n ${CONDA_ENV_NAME} --file environment.yml

# Add conda to the path
ENV PATH=/opt/conda/envs/${CONDA_ENV_NAME}/bin/:$PATH
ENV PYTHONPATH=/opt/conda/envs/${CONDA_ENV_NAME}/bin

# We now replace the image’s existing Python with Python from the conda environment:
RUN mv /var/lang/bin/python3.11 /var/lang/bin/python3.11-clean && ln -sf /opt/conda/envs/${CONDA_ENV_NAME}/bin/python /var/lang/bin/python3.11

# Clean up any dangling conda resources
RUN conda clean -afy

# Copy the function code to the LAMBDA_TASK_ROOT directory
# This environment variable is provided by the lambda base image
ADD . ${LAMBDA_TASK_ROOT}

# Install the package into the base image
RUN python -m pip install .
RUN python -m pip install stac_fastapi.types

# Set entry point
CMD [ "bin/lambda_entry.handler" ]

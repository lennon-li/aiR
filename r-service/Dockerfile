FROM r-base:4.4.2

RUN apt-get update && apt-get install -y \
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
    libsodium-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libpng-dev \
    libjpeg-dev \
    libfreetype6-dev \
    libfontconfig1-dev \
    libtiff5-dev \
    libuv1-dev \
    libudunits2-dev \
    file \
    && rm -rf /var/lib/apt/lists/*

# Use Posit Public Package Manager (PPM) binary repository for faster and more reliable installation
RUN Rscript -e "options(repos = c(CRAN = 'https://packagemanager.posit.co/cran/__linux__/bookworm/latest')); \
    install.packages(c('plumber', 'jsonlite', 'magrittr', 'ragg', 'systemfonts', 'googleCloudStorageR', 'googleAuthR', 'ggplot2', 'dplyr', 'tidyr', 'readr', 'tibble', 'stringr', 'forcats', 'purrr', 'data.table', 'scales', 'janitor', 'lubridate'))"

WORKDIR /app
COPY . .

# Ensure run.R uses the PORT env var correctly
ENV PORT=8080
EXPOSE 8080

CMD ["Rscript", "run.R"]

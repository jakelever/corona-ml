#!/bin/bash

rm -fr last_release
mkdir last_release

zenodo_get -d https://doi.org/10.5281/zenodo.4383289 -o last_release


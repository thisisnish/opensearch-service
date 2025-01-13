#!/bin/bash
#
# ecr-deploy-dev.sh
#
# Author: Lain Musgrove (lain.musgrove@hearst.com)
# Date: Wednesday November 15, 2023
#

aws ecs update-service --service marketplace-search-service-dev \
  --task-definition marketplace-search-service-dev \
  --force-new-deployment --cluster ecm-development

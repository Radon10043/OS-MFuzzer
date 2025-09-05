#!/bin/bash

get_lunch_target() {
    local BRANCH=$1
    local PRODUCT_NAME="aosp_cf_x86_64_phone"
    local RELEASE_CONFIG="trunk_staging"
    local BUILD_VARIANT="userdebug"
    local TARGET=""
    GSI_VERSION=$(echo $BRANCH | sed 's/android[-]*\([0-9]*\).*/\1/')
    case $GSI_VERSION in
        12|13|14)
            TARGET="$PRODUCT_NAME-$BUILD_VARIANT"
            ;;
        15|16)
            TARGET="$PRODUCT_NAME-$RELEASE_CONFIG-$BUILD_VARIANT"
            ;;
        *)
            echo "Unsupported branch: $BRANCH"
            exit 1
            ;;
    esac
    echo $TARGET
}
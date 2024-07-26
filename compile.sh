#!/usr/bin/env bash


usage()
{
    echo -n "############################################################
# Compile script for ltaomodcentroider milk plugin
# Customize / add you own options
# Use as-is, or make a local custom copy (private, do not commit)
############################################################

Examples:

Install to deafult directory (/usr/local)
$ $(basename $0)
$ cd build; sudo make install

Do not include Python wrapper, build in local dir
$ $(basename $0) \$PWD/local
$ cd build; make install
    "
}

if [ "$1" == "-h" ]; then
    usage
    exit 1
fi

mkdir -p build
cd build

if [ ! -z $1 ]
then
    MILK_INSTALL_ROOT=$1
fi

if [ ! -z $MILK_INSTALLDIR ]
then
    MILK_INSTALL_ROOT=$MILK_INSTALLDIR
fi

if [ -z $MILK_INSTALL_ROOT ]
then
    echo "MILK_INSTALL_ROOT not set and optional install path not provided. Exiting."
    exit 1
fi

BUILDTYPE=${MILK_BUILD_TYPE:-"Release"}

echo "Compiling"
cmake ../ltaomod_centroider/ $MILK_CMAKE_OPT -DCMAKE_INSTALL_PREFIX=$MILK_INSTALL_ROOT -DCMAKE_BUILD_TYPE=${BUILDTYPE}


NCPUS=`fgrep processor /proc/cpuinfo | wc -l`
cmake --build . -- -j $NCPUS


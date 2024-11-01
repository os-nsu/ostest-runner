#!/bin/bash


cwd=$(pwd)
p=0;
u=0;
a=0;
r=0;
b=0;
l=0;
c=0;

usage="Usage: $0 [options]
Options:
-h
    help
Required options:
-p <project_folder_name>
    name of project folder
-u <user_name>
    user name
-a <attempt>
    attempt number
-r <repository URL>
    git url repository
-b <branch>
    repository branch name
-l <lab_number>
    lab number
-c <connected_test>
    test name
    for multiple tests use -c with argument again"

while getopts p:u:a:r:b:l:c:h flag
do
    case "${flag}" in
        p) project_folder_name=${OPTARG};
        p=1;;
        u) user_name=${OPTARG};
        u=1;;
        a) attempt=${OPTARG};
        a=1;;
        r) repository_url=${OPTARG};
        r=1;;
        b) branch=${OPTARG};
        b=1;;
        l) laboratory_number=${OPTARG};
        l=1;;
        c) connected_tests+=(${OPTARG});
        c=1;;
        h) echo "$usage";
        exit 0;;

    esac
done

if [ $((p&u&a&r&b&l&c)) -ne 1 ]; then
    echo "Not all options are used"
    echo "$usage";
    exit 1;
fi
#Clone repo
mkdir labs;
cd labs;
mkdir $user_name;
cd $user_name;
git clone $repository_url;
cd $project_folder_name
git switch $branch;
cd $cwd;
#Create report folder
cd tests/reports
mkdir report_$user_name
cd report_$user_name
mkdir $project_folder_name
cd $cwd
#Clone tests 
cd tests;
git clone https://github.com/os-nsu/tests.git;
cd tests;
pip install -r requirements.txt
./run_tests.py --src ../../labs/$user_name/$project_folder_name --junit-xml=../reports/report_$user_name/$project_folder_name/report_attempt_$attempt.xml;
exit 0;

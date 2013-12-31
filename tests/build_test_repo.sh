#!/bin/sh

NAME="test_repo"
PAUSE="sleep 1"
#PAUSE="egitu ."

if [ -e $NAME ]; then
    echo "The folder test_repo already exists"
    exit 1
fi

mkdir $NAME
cd $NAME

git init
echo "first file content" >> file1.txt
git add file1.txt
git commit -m 'Initial commit'
$PAUSE

echo "first file content (v1)" >> file1.txt
git commit -a -m 'first commit in master'
$PAUSE

echo "first file content (v2)" >> file1.txt
git commit -a -m 'second commit in master'
$PAUSE


# TEST: branch1 - three commit and a fast-forward merge
git checkout -b branch1
echo "second file content" >> file2.txt
git add file2.txt
git commit -m 'first commit in branch1'
$PAUSE

echo "second file content (v2)" >> file2.txt
git commit -a -m 'second commit in branch1'
$PAUSE

echo "second file content (v3)" >> file2.txt
git commit -a -m 'third commit in branch1'
$PAUSE

git checkout master
git merge branch1
$PAUSE

git tag -a v1.0 -m 'tagging v1.0'
$PAUSE

git tag -a v1.0bis -m 'tagging v1.0 another time'
$PAUSE


# TEST: branch2 - three commit and a real merge
git checkout -b branch2
echo "third file content" >> file3.txt
git add file3.txt
git commit -m 'first commit in branch2'
$PAUSE

echo "third file content (v2)" >> file3.txt
git commit -a -m 'second commit in branch2'
$PAUSE

echo "third file content (v3)" >> file3.txt
git commit -a -m 'third commit in branch2'
$PAUSE

git checkout master
echo "first file content (v3)" >> file1.txt
git commit -a -m 'third commit in master'
$PAUSE

git merge branch2 -m 'Merge branch2 in master'
$PAUSE

git tag -a v1.1 -m 'tagging v1.1'
$PAUSE




egitu

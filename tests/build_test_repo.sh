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

git tag -a fast_forwarded_branch -m 'tagging'
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

git tag -a merged_branch -m 'tagging'
$PAUSE

git checkout master
echo "first file content (v3)" >> file1.txt
git commit -a -m 'third commit in master'
$PAUSE

git merge branch2 -m 'Merge branch2 in master'
$PAUSE

git tag -a v1.1 -m 'tagging v1.1'
$PAUSE

git tag -a v1.1bis -m 'tagging v1.1 another time'
$PAUSE


# TEST: file remove
git rm file3.txt
git commit -a -m 'removed file3'
$PAUSE

git rm file2.txt
git commit -a -m 'removed file2'
$PAUSE


# TEST: 3 different branch starting at the same point
git checkout -b branch3
echo "second file content (v4)" >> file2.txt
git add file2.txt
git commit -a -m 'first commit in branch3'
$PAUSE

git checkout master
git checkout -b branch4
echo "third file content (from branch 4)" >> file3.txt
git add file3.txt
git commit -a -m 'first commit in branch4'
$PAUSE

git checkout master
git checkout -b branch5
echo "fourth file content (from branch 5)" >> file4.txt
git add file4.txt
git commit -a -m 'first commit in branch5'
$PAUSE

git checkout master
echo "first file content (v4)" >> file1.txt
git commit -a -m 'fourth commit in master'
$PAUSE

git merge --no-ff branch3 -m 'Merge branch3 in master'
$PAUSE

git merge --no-ff branch4 -m 'Merge branch4 in master'
$PAUSE

git merge --no-ff branch5 -m 'Merge branch5 in master'
$PAUSE


# TEST: a branch that merge from master (and then continue...)
echo "first file content (v5)" >> file1.txt
git commit -a -m 'sixts commit in master'
$PAUSE

git checkout -b branch6
echo "second file content (v5)" >> file2.txt
git commit -a -m 'first commit in branch6'
$PAUSE

echo "second file content (v6)" >> file2.txt
git commit -a -m 'second commit in branch6'
$PAUSE

git checkout master
echo "first file content (v6)" >> file1.txt
git commit -a -m 'seventh commit in master'
$PAUSE

git checkout branch6
git merge master -m 'merge master in branch6'
$PAUSE

echo "second file content (v6)" >> file2.txt
git commit -a -m 'third commit in branch6'
$PAUSE

git checkout master
echo "first file content (v7)" >> file1.txt
git commit -a -m 'eightth commit in master'
$PAUSE


egitu

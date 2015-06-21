#! /bin/sh
# Script to call format generators for "raw" formats

# Copyright © 2015 Aleksey Cherepanov <lyosha@openwall.com>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

M="$1"
F="raw-$M-dk"
N=raw"`printf %s "$M" | sed -e 's/.*/\U&/'`"_my_fmt_plug

if ! printf %s "`pwd`" | grep 'john-devkit-temp$' >/dev/null; then
    echo "You should be john-devkit-temp/ folder"
    exit 1
fi

if ! test -e ../john-devkit-dirty/ ; then
    echo "There should ../john-devkit-dirty/ with all the code"
    exit 1
fi

if ! test -e JohnTheRipper/ ; then
    echo "There should JohnTheRipper/ folder here"
    exit 1
fi

echo "Writing..."
echo "Format: $F"
echo "File: $N"

python "../john-devkit-dirty/format_john_$M.py" "" "" > "JohnTheRipper/src/$N.c" && (cd JohnTheRipper/src/ && RELEASE_BLD="-Wfatal-errors -g" make -s &&  ../run/john --test=5 "--format=$F")

objdump -d "JohnTheRipper/src/$N.o" | sed -ne '/<crypt_all>/,/^$/ p' > asm && wc -l asm; perl -pe 's/[^\t]*\t//; s/\t.*//' asm | tail -n +2 | perl -pe 's/\s+//g' | perl -lne 'print(length($_) / 2, " bytes of code")'

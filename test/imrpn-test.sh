#!/bin/bash
#
. ./Test

set -o noglob

imrpn=../imrpn.py

# Test the basics
#
Test   Pass;	CompareEval "$imrpn 1" 		1
Test ! Fail;	CompareEval "$imrpn 1" 		2

Test if 1;	CompareEval "$imrpn : xx if 4 then        ; 1 xx" 4
Test if else 1;	CompareEval "$imrpn : xx if 4 else 5 then ; 1 xx" 4
Test if 0;	CompareEval "$imrpn : xx if 4 then        ; 0 xx" ""
Test if else 0;	CompareEval "$imrpn : xx if 4 else 5 then ; 0 xx" 5

Test if else 0;	CompareEval "$imrpn : xx begin i while ; 3 xx" ""


Test add;	CompareEval "$imrpn 1 1 +"	2.0
Test sub;	CompareEval "$imrpn 1 1 -"	0.0
Test mul;	CompareEval "$imrpn 1 1 *"	1.0
Test div;	CompareEval "$imrpn 1 1 /"	1.0

Test DotDot;	CompareEval "$imrpn 1 2 3"	"3
2
1"

#Test Array;	$imrpn 2 2 2 array > array.tmp
#		DiffFiles array.tmp array.fits


TestDone



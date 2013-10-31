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


Test add;	CompareEval "$imrpn 1 1 +"	2
Test sub;	CompareEval "$imrpn 1 1 -"	0
Test mul;	CompareEval "$imrpn 1 1 *"	1
Test div;	CompareEval "$imrpn 1 1 /"	1

Test add;	CompareEval "$imrpn 1 1.0 +"	2.0
Test sub;	CompareEval "$imrpn 1 1.0 -"	0.0
Test mul;	CompareEval "$imrpn 1 1.0 *"	1.0
Test div;	CompareEval "$imrpn 1 1.0 /"	1.0

Test Drop;	CompareEval "$imrpn 1 1 drop"	1
Test Dup;	CompareEval "$imrpn 1 dup +"	2
Test Swap;	CompareEval "$imrpn 1 2 swap /"	2
Test Rot;	CompareEval "$imrpn 1 2 3 rot / +"	5

Test DotDot;	CompareEval "$imrpn 1 2 3"	"3
2
1"

#Test Array;	$imrpn 2 2 2 array > array.tmp
#		DiffFiles array.tmp array.fits

Test pi;	CompareEval "$imrpn pi"	3.14159265359

Test min;	CompareEval "$imrpn pi 1 min"	
Test max;	CompareEval "$imrpn pi 1 max"	3.14159265359
Test abs;	CompareEval "$imrpn pi -1 * abs"	3.14159265359

TestDone



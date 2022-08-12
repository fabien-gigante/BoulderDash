#!/usr/bin/env bash
for img in ../res/*16-*.png; do
  echo $img "->" ${img/16/64}
  ./ScalerTest_Windows -4xbrz  $img  ${img/16/64}
done
#read -p "Press any key..."
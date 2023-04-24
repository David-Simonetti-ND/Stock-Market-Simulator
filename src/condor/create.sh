for VARIABLE in 4 5 6 7 8 9
do
    cp table0.ckpt table$VARIABLE.ckpt
    cp table0.txn table$VARIABLE.txn
done

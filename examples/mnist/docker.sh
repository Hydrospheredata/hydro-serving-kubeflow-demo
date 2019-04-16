for path in ./*
do 
    if [ -d $path ]; then
        if [ -e $path/Dockerfile ]; then
            cat $path/Dockerfile
            echo 
        fi 
    fi
done
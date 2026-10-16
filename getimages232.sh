 #!/bin/bash


cd $HOME/Downloads/svl

# Counter for naming downloaded images


#SET

IP="192.168.100.232"
LOW_FR=1
DURATION=600
#DURATION=10
HIGH_FR=1

#NOTSET



IMAGES_URL="http://$IP/capture"

	
#start loop
while true ; do
#ping check online
	if ping -c 1 -W 1 "$IP" > /dev/null; then
		echo "$IP is online. Start recording $(date +%H-%M-%S_%Y-%m-%d)"
	else
		echo "$IP is offline."
		sleep 5 
		continue
	fi
	
	#check busy hour
	current_hour=$(date +%H)
	if  [ "$current_hour" -lt 20 ]; then
		FRAME_RATE=$LOW_FR
	else 
		FRAME_RATE=$HIGH_FR
	fi
	
	#very few evnt so more sleep
	if  [ "$current_hour" -lt 5 ]; then
		sleep $LOW_FR
		echo "sleep $LOW_FR due to night"
	fi

	# set var for this loop
	RATE=$(echo "scale=2; 1 / $FRAME_RATE" | bc)
	echo "rate = $RATE"
	MAX=$((DURATION * FRAME_RATE))

	COUNTER=1
	CURRENT_DATE=$(date +%Y-%m-%d)
	CURRENT_TIME=$(date +%H-%M-%S_%Y-%m-%d)


	

	# Specify the output directory to save images
	OUTPUT_DIR="$IP/$CURRENT_DATE"
	IMAGES_OUTPUT_DIR="$OUTPUT_DIR/images_$CURRENT_TIME"
	# Create the output directory if it doesn't exist
	mkdir -p "$IMAGES_OUTPUT_DIR"
	#  loop to download the image every 0.3 seconds
	while [ "$COUNTER" -lt "$MAX" ]; do
	# Create a filename based on the counter
	FILENAME="$IMAGES_OUTPUT_DIR/image$(printf "%04d" "$COUNTER").jpg"

	# Download the image (skip timestamp/increment on failure)
	if curl -fsS -o "$FILENAME" "$IMAGES_URL"; then
		#write timestamp on it
		magick $FILENAME -gravity SouthEast -pointsize 18 -fill white -annotate +10+10 "$(date '+%Y-%m-%d %H:%M:%S')" $FILENAME

		# Increment the counter
		COUNTER=$((COUNTER + 1))
	else
		echo "Download failed for counter=$COUNTER"
		rm -f "$FILENAME"
	fi

	# Wait for x seconds
	sleep $RATE
	done

	
	
	IMAGES_DIR=$IMAGES_OUTPUT_DIR
	# Specify the output video file name
	OUTPUT_VIDEO="video_$CURRENT_TIME"
	
	# Create the video from images
	ffmpeg -loglevel error -framerate "$FRAME_RATE" -i "$IMAGES_DIR/image%04d.jpg" -c:v mpeg4 -pix_fmt yuv420p "$OUTPUT_DIR/$OUTPUT_VIDEO.mp4"
		
	if [ $? -ne 0 ]; then
	    echo "Error: ffmpeg command failed. Check error_log.txt for details."
	else
	    echo "Success: Video created successfully."
		rm -rf  $IMAGES_DIR
	fi
done

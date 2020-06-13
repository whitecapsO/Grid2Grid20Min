from farmware_tools import app
from farmware_tools import device
from farmware_tools import env
from farmware_tools import get_config_value
import json
import os

#TODO implement endLastRowGrid2

# TODO work out why it takes the Farmware librarys so long to load: 
# https://forum.farmbot.org/t/farmware-moveabsolute-and-executesequence-not-working/5784/28

# Rewrite of Grid2Grid to run in 20 minutes due to limitations put on Farmware 
# i.e. Farmware can only run for 20 minutes and there is a 2 second delay between device calls
# the only way to loop is to use sequence recursion at the end of each row 

# The way the loop works is:
# 1 - To initialise an index via a separate Farmware that sets X & Y coordinates in an environment variable to 0,0 in a config file 
# 2 - This Farmware reads the config file coordinates if they are 0,0 it assumes it is at the start
# 3 - If they are not then it assumes the co-ordinates are at the end of a row for the second grid as the co-ordinates are updated at the end of the second grid row
# 4 - If at end of row i.e. <> 0, then loop through and calculate the co-ordinates until they match what is in the config file 
# 5 - Calculate the co-ordinates one more time before upon moving to the next row
# 6 - At the end of that row write the co-ordinates to the env variable in the config file and exit the Farmware 

# There will be three calls to the device to stay within the 20 minute window as each costs 2 seconds:
# 1 - Get the current coordinates from a config file 
# 2 - At the end of a row write the current co-ordinates to the config file
# 3 - Log each move

# To work out Z axis height
# 1. To work out the X axis angle use simple trig: angle = sin(angle) = opposite \ hypotenuse i.e. angle = sin-1 (opposite \ hypotenuse)
# 2. To work out Z axis height i.e the opposite: hypotenuse = current X pos - beginining of X then opposite = sin(angle) * hypotenuse
# 3. Then add that height (the opposite) to the startZGrid value

# Remember if using alternate inbetween last row is missed so:
# Normal grid: 3 rows x 2 columns = 6 cells
# Alternate in between grid: 2 rows x 4 columns = 6 cells as last rows 2 of alternate inbetween columns missed
# Not tested turning alternate inbetween on both grids at the same time
# A better way would be to initialise 2 arrays with x,y coordinates and loop through them but this algo works

#try :
rowsGrid1 = get_config_value(farmware_name='Grid2Grid20Min', config_name='rowsGrid1', value_type=int)
colsGrid1 = get_config_value(farmware_name='Grid2Grid20Min', config_name='colsGrid1', value_type=int)
spaceBetweenRowsGrid1 = get_config_value(farmware_name='Grid2Grid20Min', config_name='spaceBetweenRowsGrid1', value_type=float)
spaceBetweenColsGrid1 = get_config_value(farmware_name='Grid2Grid20Min', config_name='spaceBetweenColsGrid1', value_type=float)
startXGrid1 = get_config_value(farmware_name='Grid2Grid20Min', config_name='startXGrid1', value_type=float)
startYGrid1 = get_config_value(farmware_name='Grid2Grid20Min', config_name='startYGrid1', value_type=float)
startZGrid1 = get_config_value(farmware_name='Grid2Grid20Min', config_name='startZGrid1', value_type=float)
begininingOfXGrid1 = get_config_value(farmware_name='Grid2Grid20Min', config_name='begininingOfXGrid1', value_type=float)
sineOfAngleXGrid1 = get_config_value(farmware_name='Grid2Grid20Min', config_name='sineOfAngleXGrid1', value_type=float)
alternateInBetweenGrid1 = get_config_value(farmware_name='Grid2Grid20Min', config_name='alternateInBetweenGrid1', value_type=int)
sequenceAfter1stGridMove = get_config_value(farmware_name='Grid2Grid20Min', config_name='sequenceAfter1stGridMove', value_type=str)
endLastRowGrid1 = get_config_value(farmware_name='Grid2Grid20Min', config_name='endLastRowGrid1', value_type=int)

rowsGrid2 = get_config_value(farmware_name='Grid2Grid20Min', config_name='rowsGrid2', value_type=int)
colsGrid2 = get_config_value(farmware_name='Grid2Grid20Min', config_name='colsGrid2', value_type=int)
spaceBetweenRowsGrid2 = get_config_value(farmware_name='Grid2Grid20Min', config_name='spaceBetweenRowsGrid2', value_type=float)
spaceBetweenColsGrid2 = get_config_value(farmware_name='Grid2Grid20Min', config_name='spaceBetweenColsGrid2', value_type=float)
startXGrid2 = get_config_value(farmware_name='Grid2Grid20Min', config_name='startXGrid2', value_type=float)
startYGrid2 = get_config_value(farmware_name='Grid2Grid20Min', config_name='startYGrid2', value_type=float)
startZGrid2 = get_config_value(farmware_name='Grid2Grid20Min', config_name='startZGrid2', value_type=float)
begininingOfXGrid2 = get_config_value(farmware_name='Grid2Grid20Min', config_name='begininingOfXGrid2', value_type=float)
sineOfAngleXGrid2 = get_config_value(farmware_name='Grid2Grid20Min', config_name='sineOfAngleXGrid2', value_type=float)
alternateInBetweenGrid2 = get_config_value(farmware_name='Grid2Grid20Min', config_name='alternateInBetweenGrid2', value_type=int)
sequenceAfter2ndGridMove = get_config_value(farmware_name='Grid2Grid20Min', config_name='sequenceAfter2ndGridMove', value_type=str)
endLastRowGrid2 = get_config_value(farmware_name='Grid2Grid20Min', config_name='endLastRowGrid2', value_type=int)

# Set config file and environment variable names
configFileName = '/tmp/farmware/config.json'
evName = 'xyCoordinates'
configContents = ''

# Initialise row (X) and column (Y) indexes for all grids
rowGrid1Index = 0
colGrid1Index = 0
rowGrid2Index = 0
colGrid2Index = 0
addToZHeightGrid1 = 0
addToZHeightGrid2 = 0

# Set constant Z positions
zPosGrid1 = startZGrid1
zPosGrid2 = startZGrid2

# Get sequence IDs if name given
if sequenceAfter1stGridMove != "":
    sequenceAfter1stGridMoveId = app.find_sequence_by_name(name=sequenceAfter1stGridMove)
else :
    sequenceAfter1stGridMoveId = 0

if sequenceAfter2ndGridMove != "":
    sequenceAfter2ndGridMoveId = app.find_sequence_by_name(name=sequenceAfter2ndGridMove)
else :
    sequenceAfter2ndGridMoveId = 0

# Get the current position for x and y from the config
with open(configFileName, 'r') as f:
    configContents = json.load(f)
    f.close()

device.log(message='Opened Config', message_type='success')

# Parse the data into variables
currentPositionXstr = str(configContents[evName]).split(",",-1)[0]
currentPositionX = int(currentPositionXstr.split('.')[0])
currentPositionYstr = str(configContents[evName]).split(",",-1)[1]
currentPositionY = int(currentPositionYstr.split('.')[0])

device.log(message='currentPositionXstr: ' + currentPositionXstr + ' currentPositionXstr:' + currentPositionYstr, message_type='success')

# Set the canMove and hasMoved flags
canMove = False
moveBeforeLastMade = False
if currentPositionX == 0 and currentPositionY == 0:
    canMove = True
    device.log(message='canMove = True', message_type='success')

# Start the first grid movement
for rowGrid1Index in range(rowsGrid1):
    # GRID 1
    #-------
    # Set first grids y position back to the first column
    yPosGrid1 = startYGrid1

    for colGrid1Index in range(colsGrid1):
        device.log(message='Grid 1 row index: ' + str(rowGrid1Index) + ' Grid 1 col index:' + str(colGrid1Index), message_type='success')
        device.log(message='Grid 2 row index: ' + str(rowGrid2Index) + ' Grid 2 col index:' + str(colGrid2Index), message_type='success')
        
        # Set the x and y positions on the first grid if alternateInBetween assume the first 
        # column is not an alternateInBetween then odd numbered colums are
        if alternateInBetweenGrid1 == 1 :
            if colGrid1Index > 0 and (colGrid1Index % 2) > 0 :
                device.log(message='Grid 1 alternateInBetween', message_type='success')
                xPosGrid1 = startXGrid1 + (spaceBetweenRowsGrid1 * 0.5) + (spaceBetweenRowsGrid1 * rowGrid1Index)
            else :
                xPosGrid1 = startXGrid1 + (spaceBetweenRowsGrid1 * rowGrid1Index)
        else :
            xPosGrid1 = startXGrid1 + (spaceBetweenRowsGrid1 * rowGrid1Index)

        device.log(message='Grid 1 x pos: ' + str(yPosGrid1) + ' Grid 1 y pos:' + str(xPosGrid1), message_type='success')

        # 1st grid move set the first grid row index back to zero if alternate inbetween column on last row let the loop handle the rest
        if ((alternateInBetweenGrid1 == 1)                  # Is alternateInBetween
        and (colGrid1Index > 0 and (colGrid1Index % 2) > 0) # is on an alternateInBetween odd numbered (offset) column  
        and (rowGrid1Index >= rowsGrid1 - 1)) :             # is on the second to last row index as an alternateInBetween has 1 less row
            # Increment y column position for grid 1
            yPosGrid1 = yPosGrid1 + spaceBetweenColsGrid1
            device.log(message='Grid 1 alternateInBetween column last row so miss a row', message_type='success')
        else :
            # Get the height additions for the Z axis if there is an x axis length and angle 
            if (begininingOfXGrid1 != 0) and (sineOfAngleXGrid1 != 0) :
                hypotenuseGrid1 = xPosGrid1 - begininingOfXGrid1
                addToZHeightGrid1 = sineOfAngleXGrid1 * hypotenuseGrid1
                
            if canMove:
                device.log('Grid 1 moving to ' + str(xPosGrid1) + ', ' + str(yPosGrid1) + ', ' + str(zPosGrid1), 'success', ['toast'])
                # Do the move and execute the sequence
                # device.move_absolute(
                #     {
                #         'kind': 'coordinate',
                #         'args': {'x': xPosGrid1, 'y': yPosGrid1, 'z': addToZHeightGrid1}
                #     },
                #     100,
                #     {
                #         'kind': 'coordinate',
                #         'args': {'x': 0, 'y': 0, 'z': 0}
                #     }
                # )

                # # Run sequence after 1st grid move
                # if sequenceAfter1stGridMove != "":
                #     device.log(message='Execute sequence: ' + sequenceAfter1stGridMove, message_type='success')
                #     device.execute(sequenceAfter1stGridMoveId)

            if endLastRowGrid1 == 1:                                # If we should end the Farmware moves after the last row of grid one then set flaf
                if ((alternateInBetweenGrid1 == 1)                  # Is alternateInBetween
                and (colGrid1Index > 0 and (colGrid1Index % 2) > 0) # is on an alternateInBetween odd numbered (offset) column  
                and (rowGrid1Index >= rowsGrid1 - 2)) :             # is on the second to last row index as an alternateInBetween has 1 less row
                     moveBeforeLastMade = True
                     device.log(message='moveBeforeLastMade = True', message_type='success')
                elif rowGrid1Index >= (rowsGrid1 - 1) :             # else if on the last row
                     moveBeforeLastMade = True
                     device.log(message='moveBeforeLastMade = True', message_type='success')

        # GRID 2
        #-------
        # Set the x and y positions on the second grid if alternateInBetween assume the first 
        # column is not an alternateInBetween then odd numbered colums are
        if alternateInBetweenGrid2 == 1 :
            if colGrid2Index > 0 and (colGrid2Index % 2) > 0 :
                device.log(message='Grid 2 alternateInBetween column', message_type='success')
                xPosGrid2 = startXGrid2 + (spaceBetweenRowsGrid2 * 0.5) + (spaceBetweenRowsGrid2 * rowGrid2Index)
            else :
                xPosGrid2 = startXGrid2 + (spaceBetweenRowsGrid2 * rowGrid2Index)
        else :
            xPosGrid2 = startXGrid2 + (spaceBetweenRowsGrid2 * rowGrid2Index)
        
        yPosGrid2 = startYGrid2 + (spaceBetweenColsGrid2 * colGrid2Index)

        device.log(message='Grid 2 x pos: ' + str(yPosGrid2) + ' Grid 2 y pos:' + str(xPosGrid2), message_type='success')

        # Get the height additions for the Z axis if there is an x axis length and angle 
        if (begininingOfXGrid2 != 0) and (sineOfAngleXGrid2 != 0) :
            hypotenuseGrid2 = xPosGrid2 - begininingOfXGrid2
            addToZHeightGrid2 = sineOfAngleXGrid2 * hypotenuseGrid2

        if canMove:
            # 2nd grid move
            device.log('Grid 2 moving to ' + str(xPosGrid2) + ', ' + str(yPosGrid2) + ', ' + str(zPosGrid2), 'success', ['toast'])

            # Do the move and execute the sequence
            # device.move_absolute(
            #     {
            #         'kind': 'coordinate',
            #         'args': {'x': xPosGrid2, 'y': yPosGrid2, 'z': addToZHeightGrid2}
            #     },
            #     100,
            #     {
            #         'kind': 'coordinate',
            #         'args': {'x': 0, 'y': 0, 'z': 0}
            #     }
            # )

            # If endLastRowGrid1 and the moveBeforeLastMade has been set then record this as the last position and stop all future moves
            if moveBeforeLastMade:
                device.log(message='canMove = False', message_type='success')
                canMove = False
                os.remove(configFileName)                           # Write the current position of the 2nd grids x,y co-ordinates to the config
                configContents = {evName: str(xPosGrid2) + "," + str(yPosGrid2)}
                with open(configFileName, 'w') as f:
                    json.dump(configContents, f)
                    f.close()

            # # Run sequence after 2nd grid move
            # if sequenceAfter2ndGridMove != "":
            #     device.log(message='Execute sequence: ' + sequenceAfter2ndGridMove, message_type='success')
            #     device.execute(sequenceAfter2ndGridMoveId)

        # Increment y column position for grid 1
        yPosGrid1 = yPosGrid1 + spaceBetweenColsGrid1

        # Set the second grid row and column indexes
        if ((alternateInBetweenGrid2 == 1)                  # Is alternateInBetween
        and (colGrid2Index > 0 and (colGrid2Index % 2) > 0) # is on an alternateInBetween odd numbered (offset) column  
        and (rowGrid2Index >= rowsGrid2 - 2)) :              # is on the second to last row index as an alternateInBetween has 1 less row
            rowGrid2Index = 0                                   # Reset row index
            colGrid2Index += 1                                  # Increment column index to move to the next column
        elif rowGrid2Index >= (rowsGrid2 - 1) :             # else if on the last row
            rowGrid2Index = 0                                   # Reset row index
            colGrid2Index += 1                                  # Increment column index to move to the next column
        else :                                              # else it's a new row 
            rowGrid2Index += 1                                  # Increment row index to move to the next row

# except :
#     pass # To ignore the error "Failed to execute command: Firmware error @ “get_position”: :farmware_exit at x=2218.2, y=41, z=0"

# AlphaLiner Serial Analyzer

## What is an AlphaLiner

An AlphaLiner is an industrial machine used in printing and packaging lines, typically for inserting, collating, or handling printed materials such as magazines, newspapers, or direct mail. It automates the process of feeding, aligning, and assembling inserts or supplements into main products, improving speed, accuracy, and efficiency in high-volume production environments.

## Analyzer Notes

- The letter **J** stands for Jacket and indicates if the pocket wheel is configured with a setting.
- The original PDF protocol documentation converted to markdown is included below (not perfect).
- This analyzer can be used to analyze data streams coming from or going to the AlphaLiner
- Not all protocol methods have been implemented (only the critical ones for collating)
- Output format ```METHOD_NAME PACKET_SEQUENCE𝑛 (DETAILS)```
- Both ACK and NAK can be hidden so they don't show in the display or export with table data.

# Protocol PC to AlphaLiner

**Document Nr.:** 7472.2003.4 / Translation Version: 1.4
**Date:** January, 11th 2007
**Author:** Thomas Annen, Urs Sommerhalder
**Contact:** urs.sommerhalder@ch.mullermartini.com

## Hardware

AlphaLiner “B&R PLC 2005” communication via serial point-to-point connection with the control system.

The following interface types are available:

*   **At the CPU:**
    *   RS422/485/TTY 347 kBaud / 4’800 baud (TTY)
    *   RS 232 57’600 baud (PG interface)
*   **At the interface module IF 050:**
    *   RS422/485 347 kBaud
    *   RS232 modem 64 kBaud
    *   RS232/TTY 64 kBaud / 4800 baud (TTY)

For cost and performance reasons, the connection via the RS422/485 or the RS232 interface is implemented in the CPU (no additional module is required). The PC requires a converter using the RS232 interface to connect to the RS422/485. The baud rate is set to 19’200.

## Telegram Data Format

*   1 start bit
*   8 data bits
*   1 parity bit, odd parity
*   1 stop bit

### Character Format

*   **Control characters** (ACK, NAK, STX, ETX) are transferred as actual characters.
*   **Data characters** (C1, C2, D1 .. Dn) the MSB (most significant bit) is always set, data range is between 0 - 127, but physically characters are transmitted between 128 - 255. A definite distinction between control characters and data characters is guaranteed.
*   The block check character is treated specially.

## Message Format

Data transfer begins with STX and ends with ETX and checksum. The first characters of the data block (C1) is a continuous message number, the second character (C2) identifies the message

`STX CHR(2) C1 CHR(128)..CHR(255) C2 CHR(128)..CHR(255) D1..Dn CHR(128)..CHR(255) BCC Block Check Character ETX CHR(3)`

### Message Number (C1)

The message number is increased sequentially with each outgoing message by one. If the message is not acknowledged with NAK or otherwise, the message number remains the same. The message number is between 0 and 127. The MSB is set always to distinguish the data from the control character.

### Message Number (C2)

The address range for the messages is between 0 and 127. The identification is transmitted with the character C2. The identification defines the message content. The MSB is set always to distinguish the data from the control character.

### Data (D1..Dn)

The data are always transferred in bytes between 128 and 255 but the effective range is between 0 . . 127 . The MSB is set always to distinguish the data from the control character.

### Block Check Characters (BCC)

The block check character is defined by an XOR operation calculated on the above defined string. The character is treated as a control character but at one of the following values it increments by one. Thus prevents from any confusion with the true control characters.

Reserved characters are:

*   STX CHR(2)
*   ETX CHR(3)
*   ACK CHR(6)
*   NAK CHR(21)
*   NUL CHR(0)

### Acknowledgement

Each message is acknowledged with ACK or NAK.

*   Successful transmission: ACK CHR (6)
*   Faulty transmission: NAK CHR (21)

## Telegram

This chapter describes all the necessary messages to connect the AlphaLiner with the control system.

**Attention!** For all data characters C and D, the MSB must be set always.

### Connection PC to AlphaLiner Manual Mode (local)

*   **Function:** Controls the Alphaliner in manual operation. The connection to the PC retains, but there are only error messages exchanged.
*   **C2 - code:** 01
*   **Data:** None
*   **Response:** The AlphaLiner updates the error messages and sends its status back, which shows either that the machine is in manual mode or in an undefined state (see status message).
*   **Note:** The manual mode (local make ready mode) is selected from the PC controller.

### Auto Mode (remote)

*   **Function:** Controls the AlphaLiner in auto mode. The PC controls production and the AlphaLiner sends all messages to the PC.
*   **C2 - code:** 02
*   **Data:** None
*   **Response:** The AlphaLiner updates the error messages and sends its status back, which shows either that the machine is in manual mode or in an undefined state (see “Status Message”).

### Diagnostic Mode

*   **Function:** If the AlphaLiner is switched in to diagnostic mode, the AlphaLiner starts a self test procedure. By means of a data byte it can distinguish between different test procedures. Error messages continue to be transmitted to the PC.
*   **C2 - code:** 03
*   **Data:** D1, D2: Reserved bytes for accurate test specifications
*   **Data Format:**
    *   D1: The bits in D1 have the following meanings:
        *   Bit 0: Test Missfeed photocell. On event, Missfeed photocell activated, the associated error light turns on.
        *   Bit 1: Lamp test. All lights flashing on the machine.
        *   Bit 2: Double detector test. Turns on the cyclical transmission of the double detector data from a feeder. The feeder number is transmitted with D2.
    *   D2: Feeder number 0 . .30 (0 = jacket feeder).
*   **Response:** The AlphaLiner updates the error messages and sends its status back, which indicates that the machine is switched to diagnose or that the machine is in an undefined state (see “Status Message”).

### Production Configuration

*   **Function:** Feeder configuration for the subsequent production.
*   **C2 - code:** 05
*   **Data:**
    *   D1.. D5: Feeder ON / OFF
    *   D6.. D10: Doublefeed control ON / OFF
    *   D11.. D15: Missfeed control ON / OFF
    *   D16 .. D20: Backup feeder
    *   D21.. D25: Low Level control ON / OFF
*   **Data Format:**
    *   Anleger = Feeder / HP=Jacket
    *   D1.. D5: A LONG-variable (32-bit) is divided into 4 bytes each at 7 bits and 1 byte of 3 bits. Bit 0 of the LONG variable (Feeder 0) corresponds to the LSB (least significant bit) of D5. Bit 30 of the variable (Feeder 30) corresponds to bit 2 of D1. A set bit corresponds to a feeder “ON”.
    *   D6 .. D10: Double detection control. The structure corresponds to the data D1.. D5: A set bit corresponds to a double control “ON”.
    *   D11.. D15: Missfeed control. See D1.. D5.
    *   D16.. D20: Backup feeder. A set bit indicates that the corresponding feeder is defined as a backup feeder to the previous feeder (feeder’s next higher number).
    *   D21.. D25: Low Level control. See D1.. D5.
*   **Response:** The AlphaLiner sends either a ready message (see “Status Message”) or a number of error messages, which indicate the feeders that are not ready. The production can begin only when the ready message has arrived. If the machine is not in auto mode a status message is sent, indicating the current mode.

### Production Order

*   **Function:** Order for production of a single copy. For each copy, synchronous to the run speed, a production order is given.
*   **C2 - code:** 06
*   **Data:**
    *   D1 .. D2: Copy ID
    *   D3 ..D7 : Selective Inserts
    *   D8: Reserved byte for further information (e.g. stacker infeed number)
    *   D9 ..D12: Number of copies (production of entire zones)
*   **Data Format:**
    *   D1 ..D2: The copy ID can take values between 1.. 8191. The number is split in two bytes. D1 contains the seven highest bits and D2 the seven lowest bits of the copy ID.
    *   D3 ..D7: The package content, as with the production configuration, is divided into 5 bytes.
    *   D8: Reserved byte for additional information. Currently not used.
    *   D9 ..D12: Number of copies. The production order defined here will be repeated according to this number (production of entire zone).
*   **Response:** If the machine is not in auto mode, a status message is sent, which indicates the current mode.
*   **Note:** A copy request with copy ID <> 0 and a package content = 0 (empty copy clock) leads to a QC test. On event “QC test” all Missfeed photocells are checked to their function. Since no paper is pulled off, the photocells must detect a reflector input, if this is not the case, the machine stops.

### Software Stop

*   **Function:** Triggering a machine stop by the PC. The machine cannot be restarted until released by the PC or an interruption of the connection.
*   **C2 - code:** 07
*   **Data:** None
*   **Response:** None (AlphaLiner will indicate error message on local error display)

### Erase Software Stop

*   **Function:** Resetting PC triggered machine stop.
*   **C2 - code:** 08
*   **Data:** None
*   **Response:** None (AlphaLiner will erase error message on local error display)

### Request for Machine Configuration

*   **Function:** Requests the mechanical machine configuration.
*   **C2 - code:** 10
*   **Data:** None
*   **Response:** Mechanical configuration (see "Machine Configuration").

### Definition Backup Feeders

*   **Function:** Defines backup feeder correcting missfeeds of another feeder. In addition a backup feeder can still be operated as a normal feeder allowing 50% “feeder batching”. A feeder can be defined as a backup for multiple feeders. The cascade of backups is also possible (4 is back up of feeder 5, 3 is back up of feeder 4, 2 is backup of feeder 3, etc.).
*   **C2 - code:** 11
*   **Data:**
    *   D1: Master Feeder (feeder number)
    *   D2: Backup Feeder (feeder number)
*   **Data Format:**
    *   D1: Feeder number of 2 . .30. Feeder 1 and Jacket feeder cannot be provided with a back up feeder.
    *   D2: Feeder number between 1 . .30. Jacket feeder can not be defined as a backup feeder.
*   **Response:** If the machine is not in auto mode, a status message is sent, which indicates the current mode.

### Number of Consecutive Errors

*   **Function:** Specific setting of allowed consecutive errors at the different controls.
*   **C2 - code:** 12
*   **Data:**
    *   D1: Control type
    *   D2: Location of the control (feeder number)
    *   D3: Number of consecutive errors allowed
*   **Data Format:**
    *   D1: Control type:
        *   0: Missfeed control
        *   1: Double feed control
        *   2: Opening control
        *   3: Profile control
        *   4: Tolerance of the double detection control
        *   5: Gap control
    *   D2: Feeder number between 0 . .30. Jacket feeder is number 0 and with 99 all feeder are defined simultaneously. When defining the opening, profile and gap control, this value is ignored.
    *   D3: Number of allowed consecutive errors. The value of 0 will cause that machine never stops. When defining the double detector tolerance, D3 has the following meaning:
        *   0: 1/1 All measurements in the range ± 1/1 of the reference value are considered as good copies. (0 x reference value < measured product thickness <2 x reference value)
        *   1: ½ All measurements in the range ± 1/2 of the reference value are considered as good copies. (0.5 x reference value < measured product thickness <1.5 x reference value)
        *   2: ¼
        *   3: 1/8
        *   4: 1/16
*   **Response:** If the machine is not in auto mode, a status message is sent, which indicates the current mode.

### Pocket and Gripper Silence

*   **Function:** To silence a defective pocket or gripper.
*   **C2 - code:** 13
*   **Data:** D1 .. D2: Status and gripper / pocket number.
*   **Data Format:** D1 .. D2 : D1 be used in bits 5 and 6 as definition bits. The remaining bits are used to transfer the pocket or gripper (1 . .4095). Number 0 means that the message corresponds to all grippers or pockets.
    *   Bit 6 : 1 = defective 0 = repaired
    *   Bit 5: 1 = gripper 0 = pocket
    *   Ein = ON; Aus = OFF
*   **Response:** None

### Forced Rejects

*   **Function:** Forced reject of a copy at the waste gate. At the time this telegram arrives, the product with the copy ID is traced between the 1st feeder (jacket or insert) and the waste gate. If it is found, that OK-flag will be deleted.
*   **C2 - code:** 14
*   **Data:** D1 .. D2: ID of the copy to be rejected.
*   **Data format:** D1 .. D2: Copy ID between 1 . .8191.
*   **Response:** None

### Delete Production Data

*   **Function:** Deletes all the production data corresponding to an AlphaLiner power up. It is needed after the PC had a power up but not the Alphaliner. This prevents that old production data are reported back what could lead to a malfunction.
*   **C2 - code:** 15 (RMDelPrd)
*   **Data:** None
*   **Response:** None

### Disable Green Lights (Feeder Assignment)

*   **Function:** Disables green feeder assignment lights.
*   **C2 - Code:** 16
*   **Data:** Lights ON / OFF
*   **Data Format:** Anleger = Feeder ; HP = Jacket
    *   D1..D5: A LONG variable (32-Bit) divided in 4 bytes for every 7 bits and 1 byte for 3 bit. The bit 0 of LONG variable (feeder 0) corresponds to the LSB (least significant bit) of D5. The bit 30 of variable (feeder 30) corresponds to the bit 2 of D1. A set bit corresponds to suppressing the green light.
    *   Light OFF / Suppressed (disabled). This means, the green light is ON, if the feeder is configured and the bit from this telegram is not set or such a telegram were never dispatched.
    *   Bit logical 0 green light enabled
    *   Bit logical 1 green light disabled
*   **Response:** None

### Control Commands

*   **Function:** Various control commands to the AlphaLiner. These functions are required for commissioning and for service purposes.
*   **C2 code:** 100
*   **Data:** D1, D2: control bytes
*   **Data Format:**
    *   D1:
        *   Bit 0: configuration upload
        *   Bit 1: load default configuration and save to FIXRAM
        *   Bit 2: Recalculate PLC
        *   Bit 3: Save your settings into FIXRAM
        *   Bit 4: PLC - Init
        *   Bit 5: PLC - TotalInit
        *   Bit 6: Upload service data
    *   D2:
        *   Bit 0: Burn configuration
*   **Response:** None

### Parameter Data

*   **Function:** Download the settings. This function is used for commissioning and required for service purposes.
*   **C2 code:** 101
*   **Data:** D1: DataID, D2..D8: Configuration Data
*   **Data Format:**
    *   D1: DataID (0 . .127)
        *   The data IDs 0. .30 correspond to the feeder numbers. The remaining data are transmitted with IDs 50. The numbers in parenthesis denote the corresponding data bytes.
        *   0. .30 : Feeder Distances
            *   AbzugDist (D2, D3)
            *   FehlDist (4, 5) [cfg11]
            *   DoppDist (6, 7) [cfg12]
            *   Status (8)
                *   The status byte, the bits have the following meanings:
                    *   Bit 0: Enable Solenoid Feed Valve
                    *   Bit 1: Enable Missfeed Control
                    *   Bit 2: Enable Double feed Control
                    *   Bit 3: Enable Hopper Empty Control
                    *   Bit 4: Enable Level Control
        *   50: Oeff - (2,3), Prof - Distanz (4,5), Taschenrad - Offset (6,7), Dickenmessungs - Toleranz (8)
        *   51: Space - Distanz (2,3), Dopp - Offset (4), Fehl - Offset (5), Offset1_2 (6), Offset1_3 (7)
        *   52: Maku - (2,3), Entnahme - (4,5), Vorausschleusungs - Distanz (6,7), Offset Delivery - Kontrolle (8)
        *   53: Beilagen - (2,3), HP - (4,5), Entnahme - Offset (6,7), Wiederholungen im Reperaturbetrieb (8)
        *   54: Exceptionhandler (2), Sprache (3), Enable Taschenrad - (4), Enable Beilagen - (5), Enable HP - (6), Enable Entnahme - Synchronisation (7), Enable Reperaturbetrieb (8)
        *   55: Sensoren - (2..6), Aktoren - Logik (7,8)
        *   56: Enable Öffnungskontrolle (2), Enable Lückenkon - trolle Beilagen (3), Enable Falschabzugkontrolle (4), Enable Simulation (5), Enable Profilkontrolle (6), Enable Delivery - Kontrolle (7)
        *   57: Enable Vorausschleusung (2), Enable Makulaturausschleusung (3), Enable HPCheck (4), Enable Leerkontrolle (5), Enable Staukontrolle (6), Maschinentyp (7)
        *   58: Grösse Hauptmodul (2), Referenz der Nettostückzahl (3), Incgeber - Auflösung (4), Taktteiler (5), Anzahl der simulierten Module (6)
        *   59: Entnahme - Status (2), Entnahme - Takte (3), Lücken - Grösse (4), max. Delivery - Fehler (5)
        *   60: max. Fehlbogen (2), max. Falschabzüge (3), max. Doppelabzüge (4), max. Öffnungsfehler (5), max. Profilfehler (6), Aussetztakte im Partnerbetrieb (7), max. Lückenfehler (8)
        *   61: max. Tipptastenverzögerung (2), max. Tippstart - Verzögerung (3,4), Horndauer (5,6)
        *   62: Wartedauer zwischen erstem und zweitem Betätigen der Starttaste (2,3), max. Startverzögerung (4,5), max. Anlaufverzögerung (6,7), Delay beim Beschreiben der Anzeigen (8)
        *   63: Zykluszeit der Geschwindigkeitsberechnung (2,3), Verzögerung der Stoppkreisüberwachung (4), Stoppkreis - Resetdauer (5,6)
        *   64: RIO - Timeout (2,3), Periodendauer der Tipp lampe (4,5), Periodendauer der Fehlerlampe (6,7)
        *   65: Portnummer (2), Porttyp (3), Databits (4), Stopbits (5), Parität (6), Baudrate (7,8)
        *   66: Anzahl Taschen (2), Taschen - Offset (3), Anzahl Klammern (4,5), Klammer - Offset (6,7)
        *   67: Distanz Leertaschenkontrolle (2,3), Fenster zu Leertaschen - kontrolle (4)
        *   127: Anforderung einer Empfangsbestätigung (letzte Meldung der Datenübertragung)
    *   A detailed description of each parameter can be found in the document "EM1_DVnn.DOC".
    *   D2..D8 : 7 byte data into 7 - BYTE, WORD - 3 and 1 BYTE, 1 LONG and 1 BYTE variable or a combination thereof. A WORD variable (16 - bit) is divided into two bytes each at 7 Bits (MSB is reserved). The range of values is a result by lower two bits (0..65535 instead of 0.. 16383). This restriction leads to no problems at the moment, because the values vary in each case less than 16383. The same procedure applies to BYTE and LONG.
*   **Response:** At the DataID 127 the PLC sends a status message with the data set ready bits of the PC. Only when the message arrives, the whole record has been transmitted correctly.

### Connection AlphaLiner to PC Status Message

*   **Function:** Status report.
*   **C2 - code:** 01
*   **Data:** D1 .. D2: Status bytes.
*   **Data Format:**
    *   D1: The bits of the first status byte are defined as follows:
        *   Bit 0 = 0 AND bit 1 = 0: mode = NotDefined
        *   Bit 0 = 1 AND bit 1 = 0: mode = Manual
        *   Bit 0 = 0 AND bit 1 = 1 : Mode = Automatic
        *   Bit 0 = 1 AND bit 1 = 1: mode = Diagnosis
        *   Bit 2 = 1: ReadyToGo
    *   D2: The bits of the second status byte are defined as follows:
        *   Bit0 = 1: end of the configuration data (Data Ready bit).
*   **Response:** None

### Error Messages

*   **Function:** Sending a message to the PC.
*   **C2 - code:** 02
*   **Data:** D1: Fault, D2: Cause, D3: Priority
*   **Data Format:**
    *   D1: Value between 0 .. 99
    *   D2: Value between 0 . .99
    *   D3: Value between 0 . .99
    *   If the priority is 0, the error is cleared. If all three values are = 0 (D1.. D3), the entire fault pool is cleared.
*   **Response:** None

### Statistical Messages

*   **Function:** Report error messages for the statistics.
*   **Attention!** This message will only occur when transmitting an error which doesn’t automatically result in a faulty product (missfeeds with backup feeder). Otherwise, only the message for a faulty product is submitted (C2 = 5).
*   **C2 - code:** 03
*   **Data:** D1: Error, D2.. D3: Error Location, D4.. D5: CopyID
*   **Data Format:**
    *   D1: Error:
        *   0: Other Errors
        *   1: Missfeed
        *   2: Doublefeed
        *   3: Opening Error
        *   4: Profile Error
        *   5: Defective Pocket
        *   6: Defective Gripper
        *   7: Maximum Number of Repair Attempts
        *   8: Gap Errors
        *   9: Controlled Forced Reject
        *   10: Wrongfeed
        *   11: Clutch
        *   12: Package Removed from Gripper Chain
        *   13: Mode Change
        *   14: Empty Pocket Error
    *   D2..D3: Depending on the error, with these two bits additional information are transferred:
        *   Miss- / Doublefeeds : Feeder number
        *   Wrongfeeds : Feeder number
        *   Opening Error: Pocket number
        *   Defective Pocket : Pocket number
        *   Profile Error: Gripper number
        *   Defective Gripper : Gripper number
        *   Copy Error in the Chain (error 12): Gripper number
        *   Clutch : Insert Feeder Module number, 99 = Pocket Wheel / Jacket Feeder
    *   D4.. D5: Copy ID between 1 . .8191.
*   **Response:** None

### Feed back of a Completed Copy

*   **Function:** Each copy that leaves the machine is reported by this telegram.
*   **C2 - code:** 04
*   **Data:** D1 .. D2: Copy ID, D3..D4 : Gripper number, D5..D9: Table of available inserts
*   **Data Format:**
    *   D1..D2: The copy ID can take values between 1.. 8191. The number is split in two bytes. D1 contains the six highest bits and D2 the seven lowest bits of the copyID. The MSB of D1 is reserved for the indication of whether it is a good or a faulty copy. Bit 6 = 1: Good copy
    *   D3..D4: The gripper number can range between 1.. 4095. The number is split into two bytes. D3 contains the five highest bits and D4 the seven lowest bits of the gripper number.
    *   D5..D9: The table of the insert, as with the production configuration, is divided into 5 bytes.
*   **Response:** None

### Feedback of a Faulty Copy

*   **Function:** On error each faulty copy is immediately is transmitted to the PC.
*   **C2 - code:** 05
*   **Data:** D1: Error, D2..D3: Error Location, D4..D5: Copy ID, D6..D10: Table of the current inserts
*   **Data Format:** D1..D5: See “Statistical Messages” (C2 = 3), D6..D10: The table of the insert, as with the production configuration, is divided into 5 bytes.
*   **Response:** None

### Machine Configuration

*   **Function:** This message transmits the mechanical configuration of the AlphaLiner to the PC requested by the PC (see "Configuration Requirements").
*   **C2 - code:** 06
*   **Data:** D1: Number of Feeders, D2..D6: Double Detectors Existing
*   **Data Format:** D1: Value between 0 . .30, D2..D6: The data format is the format of the “Production Configuration Message”. Each bit corresponds to an existing double detector.
*   **Response:** None

### Copy Inhibit Request

*   **Function:** After this message, the PC's internal clock cycle tracing shall skip a copy cycle. This message is needed for shifts in the transfer buffer and skipping of defective pockets and grippers
*   **C2 - code:** 07
*   **Data:** None
*   **Response:** None

### Configuration Data Feature

*   **Function:** Upload the machine settings
*   **C2 code:** 101
*   **Data:** D1: DataID, D2..D8: Configuration Data
*   **Data Format:**
    *   D1: Data IDs 0. . 30 corresponds with the feeder numbers. The remaining data is transmitted with ids ≥ 50. The Data IDs are identical to the “Parameter Message PC to Alphaliner”. In addition, the following data are known.
        *   100: Application configuration file (2,3), software (5), PG - version (6.7), software - index (8)
        *   101: Day (2), month (3), year (4, 5), bug fix - version (6,7)
        *   102: Release (2,3), frame driver version (4.5), RIOVersion
        *   103: Online data for testing purposes: Offset by TR (2) MJ (3), inserts (4), removal (5), number of pockets (6), gripper number (7.8)
        *   104: Project (2.3)
    *   D2.. D8: 7 byte data into 7 - BYTE, WORD - 3 and 1 BYTE, 1 LONG and 1 BYTE variable or a combination thereof. A WORD variable (16 - bit) is divided into two bytes each at 7 bits (MSB is reserved). The range of values is a result by lower two bits (0.. 65535 instead of 0 .. 16383). This restriction leads to no problems, since the values in each case will be smaller than 16383. The same procedure applies to BYTE and LONG. The transfer of the entire parameter data goes always with a status message with data set, ready bit completed (monitoring of data consistency).
*   **Response:** None

### Double Detector Test Messages

*   **Function:** This message transmits the measured values from the PLC of the Doublefeed control. These values can be provided with the test software (RECORD REPLAY) or with the AlphaLiner configuration software.
*   **C2 code:** 120
*   **Data:** D1: Feeder number, sensor number, copy available, D2, D3: value of the thickness measurement, D4, D5: Calculated mean, D6: Status
*   **Data Format:**
    *   D1: Feeder number (0. .30 ). Bit 6 is the sensor number (0. . 1). Bit 5 indicates whether a copy was pulled off or not (gripper empty or full).
    *   D2, D3: Value of the thickness measurement
    *   D4, D5: Calculated mean. If a copy is available is the mean value of the full gripper, otherwise the empty gripper is transmitted.
    *   D6: If a faulty copy is detected by the PLC, the bit 0 is set in D6.
*   **Response:** None

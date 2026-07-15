
PreAmp:

Video for PreAmp (also talked about z-controller boards), part 1: 
https://drive.google.com/file/d/1hix7r5ol7p9WjFohcujht9YvlXSEAAQE/view?usp=sharing

In attendance: William, Ko, Chudi, Steve, Thant, Oleksii, Spencer, Matthew
Later: Ulisses

Transimpedance Amplifier

– Allows us to get a very high voltage from a small current change

Impedance in DC: Impedance simplifies to resistance in DC circuits because there is no frequency component in a DC signal. Capacitors act as open circuits (no current flows through them), and inductors act as short circuits (like a simple wire) after any transient response has settled. Hence, only resistance matters in DC conditions.

This is hanging in

Image Label: PREAMP_ORIG_1
Notice that the 100M ohm Ohmite resistor is hanging above the board because, we want to avoid current leaks through through the PCB Surface

Image Label: PREAMP_ORIG_2
Historically
The OpAmp sense wire (negative input) pin is lifted off the PCB manually, and soldered to a post that holds the prope tip wire (and may also connect to one end of the main gain resistor)

Ideal design parameters for the input sense wire
As short as possible, less of an antenna
Shielded for as long as possible, less of an antenna
Should be in an isolated environment, faraday cage

Possible improvement, use a shielded SMA cable:
 
Could this SMA add the wrong impedance
Spencer mentions it depends on the chip bandwidth
Signal reflections depend on the frequency of the chip



The connection to the pin socket is mechanical and electrical. It must be secure conductive even in vibration or movements

Notes:
Don’t be cheap here, tolerance matters

Note
The
The movement of the piezo needs to have negligible torque from the wire, otherwise the positional data will be off

Feedback circuits with OpAms have almost immediate response time, which is way faster than sending to a microcontroller

Dan’s Design - uses feedback circuit for locking of the piezo Z-axis (high speed)
MechPanda - used a feedback through the microcontroller


Control Board OpAmps:
3x - https://www.lcsc.com/product-detail/Precision-Op-Amps_Texas-Instruments-OPA2227P_C1346534.html
1x - https://www.lcsc.com/product-detail/Operational-Amplifier_Analog-Devices-LT1469IN8-PBF_C663979.html


https://dberard.com/home-built-stm/electronics1/

1x a pin connector, maybe something like
https://www.mouser.com/ProductDetail/Molex-FCT/172704-0152?qs=Fg5TsMy7H4sQV9EpViPhJQ%3D%3D&mgh=1&gQT=1
Possibly something like this - https://www.digikey.com/en/products/detail/te-connectivity-aerospace-defense-and-marine/204351-1/299512




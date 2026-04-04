#include <Arduino.h>
#include <SPI.h> // include the SPI library
#include "stm_firmware.hpp"

#define CMD_LENGTH 4
STM stm = STM();

// Serial Commnications
void serialCommand(String command, STM &stm)
{

  if (command.length() == CMD_LENGTH)
  {
    // Reset
    if (command == "RSET")
    {
      stm.reset();
    }
    // Bias control
    if (command == "BIAS")
    {
      int value = Serial.parseInt();
      stm.set_dac_bias(value);
    }
    // Stepper motor control
    if (command == "MTMV")
    {
      int value = Serial.parseInt();
      stm.move_motor(value);
    }
    // Stepper motor Off 
    if (command == "MTOF")
    {
      stm.motoroff();
    }    
    // Stepper motor direction - affects all movements and approach
    if (command == "MTDR")
    {
      int direction = Serial.parseInt();
      stm.setMotorDirection(direction);
    }    

    // DAC control
    if (command == "DACX")
    {
      int value = Serial.parseInt();
      stm.set_dac_x(value);
    }
    if (command == "DACY")
    {
      int value = Serial.parseInt();
      stm.set_dac_y(value);
    }
    if (command == "DACZ")
    {
      int value = Serial.parseInt();
      stm.set_dac_z(value);
    }
    // ADC READ
    if (command == "ADCR")
    {
      int val = stm.read_adc();
      Serial.println(val);
    }
    // Get status
    if (command == "GSTS")
    {
      char buffer[100];
      stm.get_status().to_char(buffer);
      Serial.println(buffer);
    }

    // Approach
    if (command == "APRH")
    {
      int adc_target = Serial.parseInt();
      int steps = Serial.parseInt();
      stm.start_approach(adc_target, 10000, steps);
    }
    // Measure rawIV and dIdV
    if (command == "IVME")
    {
      int bias_start = Serial.parseInt();
      int bias_end = Serial.parseInt();
      int bias_step = Serial.parseInt();
      //stm.generate_iv_curve(bias_start, bias_end, bias_step);
      stm.generate_iv_didv_curve(bias_start, bias_end, bias_step);
    }
    if (command == "IVGE")
    {
      //stm.send_iv_curve();
      stm.send_iv_didv_curve();
    }
    // Measure dIdZ
    if (command == "DIME")
    {
      int z_start = Serial.parseInt();
      int z_end = Serial.parseInt();
      int z_step = Serial.parseInt();
      stm.generate_dIdZ_curve(z_start,  z_end,  z_step);
    }

    if (command == "DIGE")
    {
      stm.send_dIdZ_curve();
    }

    if (command == "NOIS") // start noise scan
    {
      int xres = Serial.parseInt();
      int yres = Serial.parseInt();
      int spp = Serial.parseInt();
      int uS = Serial.parseInt();
      stm.noise_scan(xres,yres,spp,uS);
    }


    if (command == "GSPC") // global spectroscopy
    {
      int x_start = Serial.parseInt();
      int x_end = Serial.parseInt();
      int x_res = Serial.parseInt();
      int y_start = Serial.parseInt();
      int y_end = Serial.parseInt();
      int y_res = Serial.parseInt();
      int bias_start = Serial.parseInt();
      int bias_end = Serial.parseInt();
      int bias_points = Serial.parseInt();      
      int mode = Serial.parseInt();  //    mode = 0 → IV  mode = 1 → dIdV
      stm.start_grid_spectroscopy(x_start,  x_end,  x_res,
                                  y_start,  y_end,  y_res,
                                   bias_start,  bias_end,  bias_points, mode );
    }


    // Start const current mode
    if (command == "CCON")
    {
      int adc_target = Serial.parseInt();
      stm.turn_on_const_current(adc_target);
    }
    // Turn off const current
    if (command == "CCOF")
    {
      stm.turn_off_const_current();
    }
    // Setup PID values
    if (command == "PIDS")
    {
      double Kp = Serial.parseFloat();
      double Ki = Serial.parseFloat();
      double Kd = Serial.parseFloat();
      stm.Kp = Kp;
      stm.Ki = Ki;
      stm.Kd = Kd;
    }
    if (command == "SCST")
    {
      int x_start = Serial.parseInt();
      int x_end = Serial.parseInt();
      int x_resolution = Serial.parseInt();
      int y_start = Serial.parseInt();
      int y_end = Serial.parseInt();
      int y_resolution = Serial.parseInt();
      int sample_per_pixel = Serial.parseInt();
      stm.start_scan(x_start, x_end, x_resolution, y_start, y_end, y_resolution, sample_per_pixel);
    }
    if (command == "TEST")
    {
      stm.test_piezo();
    }
    if (command == "STOP")
    {
      stm.stm_status.is_approaching = false;
      stm.stm_status.is_const_current = false;
      stm.stm_status.is_scanning = false;
    }
    if (command == "SETL")
    { 
       
       stm.piezo_x_settle_uS = Serial.parseInt();
       stm.piezo_y_settle_uS = Serial.parseInt();
       stm.piezo_z_settle_uS = Serial.parseInt();    
       stm.bias_settle_uS = Serial.parseInt();  
    }    
  }
}

void checkSerial(STM &stm)
{
  String serialString;
  if (Serial.available() > 0)
  {
    for (int i = 0; i < CMD_LENGTH; i++) // Read command with length CMD_LENGTH
    {
      // delay(1);
      char inChar = Serial.read();
      serialString += inChar;
    }
    serialCommand(serialString, stm);
  }
}


void setup()
{
  // initialize the serial port
  Serial.begin(921600); //115200
  // initialize SPI:
  SPI.begin();
  // Set Up SPI1 for Teensy 4.1
  SPI1.setSCK(27);
  SPI1.setCS(38);
  SPI1.setMISO(39);
  SPI1.begin();
  // Reset all;
  stm.reset();
  stm.SetDefaults();
  // Init
}

void loop()
{
  checkSerial(stm);
  stm.update();
  if (stm.stm_status.is_approaching)
  {
    stm.approach();
  }
  if (stm.stm_status.is_const_current)
  {
    stm.control_current(stm.read_adc_raw());
  }
}

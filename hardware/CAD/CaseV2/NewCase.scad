cx = 110;
cy = 210; //130 + 40 + 40
cz = 50;
mz = 40; // mid level z height
th = 10; // thickness of the walls


PCBX = 88;
PCBY = 103;
PCBZ = 1.5;

module CBCutout()
{
    cube([cx-th/2,cy-th/2,10],true);
}

module caseBase()
{
    difference()
    {
        union()
        {
            difference ()
            {
                cube([cx,cy,cz],true);
                translate([0,0,th])
                    cube([cx-th,cy-th,cz],true);
            }
            translate([0,0,-cz/2])
                cylinder(h = cz, r = 6, $fn =99);
            translate([30,50,-cz/2])
                cylinder(h = cz, r = 6, $fn =99);
            translate([-30,50,-cz/2])
                cylinder(h = cz, r = 6, $fn =99);
            translate([30,-50,-cz/2])
                cylinder(h = cz, r = 6, $fn =99);
            translate([-30,-50,-cz/2])
                cylinder(h = cz, r = 6, $fn =99);
        }
    translate([0,0,cz-25])
        CBCutout();
        
       
    translate([30,80,(-cz/2) + 5])
    roundMagnet();
    translate([-30,80,(-cz/2) + 5])
    roundMagnet();
    translate([30,-80,(-cz/2) + 5])
    roundMagnet();
    translate([-30,-80,(-cz/2) + 5])
    roundMagnet();
    }
}

module CMCutout()
{
    
    difference ()
    {
        cube([cx+th,cy+th,cz],true);
        translate([0,0,th])
            cube([cx-th/2,cy-th/2,cz],true);
    }
}

module DSub()
{
    cube ([20,32,15],true);
}

module caseMid()
{
    union()
    {
        difference ()
        {

            union(){
                difference()
                {
                    cube([cx,cy,mz],true);
                    translate([0,0,th])
                        cube([cx-th,cy-th,cz],true);
                }
                postpattern();
                postpattern2();
            }
                
            translate([0,0,-40])
            CMCutout();            
        
            offset = 28;
            translate([-50,offset,-1])
            DSub();

            translate([-50,-offset,-1])
            DSub();
            //wirecutout
            translate([-50,0,0])
            cube([20,20,10],true);
            
            translate([0,0,mz -20])
                CBCutout();
                
            translate([0,0,15])
                boltpattern();                
            translate([0,62.5,-20])
                cube([30,15,40],true);              
       }
    translate([-6,0,(-mz/2) +7 ])
    PCBRest();    
    }
  
}


module casetop()
{
    difference()
    {
        cube([cx,cy,10],true);
            translate([0,0,mz -65])
                    CMCutout();    
                
        translate([30,80, 0])
        roundMagnet();
        translate([-30,80, 0])
        roundMagnet();
        translate([30,-80,0])
        roundMagnet();
        translate([-30,-80,0])
        roundMagnet();   
        translate([0,0,2])
            barMagnetGroup();   
            
        boltpattern(); // the 2 fasteners
        boltpattern2();
    }                 
}


module casefloat()
{
    difference()
    {
        cube([cx,cy,10],true);  
                
        translate([30,80, -5.15])
        roundMagnet();
        translate([-30,80, -5.15])
        roundMagnet();
        translate([30,-80,-5.15])
        roundMagnet();
        translate([-30,-80,-5.15])
        roundMagnet();   

        boltpattern2();
        translate([0,0,-4])
            AlumSquare ();        

        translate([0,0,37.5])
            boltpattern3(30,55);
    }

}

module cover()
{
                import("./STM_ShieldingBoxBase_Longboard_TM13.stl");
       // }

}

module casefloattop()
{
    color([.40,.40,1])
    difference()
    {
        translate([35,-55,40])
        {
            rotate([0,0,90])        
                import("./STM_ShieldingBoxBase_Longboard_TM13.stl");
        }
        
        translate([0,0,37.5])
            boltpattern3(30,55);
    }
}

module AlumSquare()
{
    cube([101.25,101.25,12],true);
}
module PCB()
{
    cube ([PCBX,PCBY,PCBZ],true);
}

module PCBRest()
{
    difference(){
    cube ([PCBX,PCBY,5],true);
        translate([0,0,-1])
        cube ([PCBX-3,PCBY-3,7],true);
    }
}

/*The cut out that we're using for a 3mm bolt */
module boltcutout()
{
    //3.5 &6.5? 
    rotate([0,180,0])
    union(){
    cylinder(r=4/2, h =40, $fn =99);
    cylinder(r=7/2, h =4, $fn =99);
    }
}


module postpattern()
{
    yoff = 80;
    rad = 6;
    translate([0,yoff,-mz/2])
        cylinder(r=rad, h =mz, $fn =99);
    translate([0,-yoff,-mz/2])
        cylinder(r=rad, h =mz, $fn =99);
}

module pp2()
{
rad = 6;
    difference()
    {
        cylinder(r=rad, h =mz, $fn =99);
        translate([0,0,-1])
            cylinder(r=3.9/2, h =mz + 2, $fn =99);
    }    
}

module postpattern2()
{
    xoff = 30;
    yoff = 80;
    translate([xoff,yoff,-mz/2])
        pp2();
    translate([xoff,-yoff,-mz/2])
        pp2();
    translate([-xoff,yoff,-mz/2])
        pp2();
    translate([-xoff,-yoff,-mz/2])
        pp2();
}

module boltpattern2(xoff = 30,yoff = 80)
{
    //xoff = 30;
    //yoff = 80;
    translate([xoff,yoff,-mz/2])
        cylinder(r=3.9/2, h =mz + 2, $fn =99);
    translate([xoff,-yoff,-mz/2])
        cylinder(r=3.9/2, h =mz + 2, $fn =99);
    translate([-xoff,yoff,-mz/2])
        cylinder(r=3.9/2, h =mz + 2, $fn =99);
    translate([-xoff,-yoff,-mz/2])
        cylinder(r=3.9/2, h =mz + 2, $fn =99);
}

module boltpattern3(xoff = 30,yoff = 80)
{
    translate([xoff,yoff,-mz/2])
        boltcutout();
    translate([xoff,-yoff,-mz/2])
        boltcutout();
    translate([-xoff,yoff,-mz/2])
        boltcutout();
    translate([-xoff,-yoff,-mz/2])
        boltcutout();
}

module boltpattern()
{
    yoff = 80;
    translate([0,yoff,6])
        boltcutout();
    translate([0,-yoff,6])
        boltcutout();
}

module barMagnetGroup()
{
    translate([0,0,0])
        barMagnetCutout();
    translate([0,-15,0])
        barMagnetCutout();
    translate([0,15,0])
        barMagnetCutout();
    translate([0,-30,0])
        barMagnetCutout();
    translate([0,30,0])
        barMagnetCutout();

    translate([40,0,0])
    rotate([0,0,90])
        barMagnetCutout();

    translate([-40,0,0])
    rotate([0,0,90])
        barMagnetCutout();

}

module barMagnetCutout()
{
// 60,10,3
    cube([60.5,10.5,7],true);
}

module roundMagnet()
{
//really 5mm high, but we're using these as cutouts
    cylinder(h= 6,r = 30/2, $fn =99);
}

//caseBase();
//translate([0,0,cz+10])
//caseMid();
/*
translate([0,0,cz+cz])
casetop();
translate([0,0,140])
casefloat();
translate([0,0,150])
casefloattop();
*/


casefloat();

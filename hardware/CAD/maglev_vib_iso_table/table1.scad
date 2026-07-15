//alumXY = 6 * 25.4;
alumXY = (4 * 25.4)+.5;
alumZ = .5*25.4; 

tableXY = 4.25 * 25.4;

magdiam = 19.1;//30.0;//29.5;
magZT = 6.5;
magZB = 5;
//stabrad = 3.25;// stabilizer rod radius
//stabrad = 5;// stabilizer rod radius
wallt = 3;
offset = 2.5;

module alum()
{
    color("silver")
    cube([alumXY,alumXY,alumZ],true);
}

//29.5x4.9
module Magnet30x5()
{
    difference(){
    cylinder(r = magdiam/2,h=magZ,$fn = 99);
    translate([0,0,1])
    cylinder(r = 5/2,h=magZ+2,$fn = 99);
    }
}

module MagnetBar()
{
    cube([10,60,3],true);
}

module MagnetBar3x()
{
    cube([10,60.5,9],true);
}

module MagHolder(stab,magh)
{
    difference()
    {
        cylinder(r = (magdiam/2) + wallt  ,h=magh + 3, $fn =99);
        translate([0,0,wallt*2 -1])
            cylinder(r = (magdiam/2),h=magh +2, $fn =99);
        translate([0,0,-1])
            cylinder(r = (stab/2),h=8, $fn =99);
    }
}

module TopTable()
{
    stabt = 5;
    difference()
    {
        union(){
            translate([tableXY/2 + ((magdiam/2) - offset ),(tableXY/2)+ ((magdiam/2) - offset),0])
                MagHolder(stabt,magZT);
            translate([-(tableXY/2 + ((magdiam/2) - offset)),(tableXY/2)+ ((magdiam/2) - offset),0])
                MagHolder(stabt,magZT);
            translate([-(tableXY/2 + ((magdiam/2) - offset)),-((tableXY/2)+ ((magdiam/2) - offset)),0])
                MagHolder(stabt,magZT);
            translate([tableXY/2 + ((magdiam/2) - offset),-((tableXY/2)+ ((magdiam/2) - offset)),0])
                MagHolder(stabt,magZT);
                
            translate([0,0,alumZ/2])        
                cube([tableXY,tableXY,alumZ],true);
        }
        translate([0,0,alumZ/2 + wallt])        
            cube([alumXY,alumXY,alumZ],true);
    //}
    translate([-40,-40,12])        
    holepattern();
    }
}
//3.7mm diam

module holepattern()
{
    for ( x = [0 : 4] )
    {
        for ( y = [0 : 4] )
        {
        translate([x*20,y*20,-15])
            cylinder(h=30,r=3.5/2,$fn = 99);
        }    
    }
}



module BottomTable()
{
    stabb = 4;
    difference()
    {
        union(){
            translate([tableXY/2 + ((magdiam/2) - offset),(tableXY/2)+ ((magdiam/2) - offset),0])
                MagHolder(stabb,magZB);
            translate([-(tableXY/2 + ((magdiam/2) - offset)),(tableXY/2)+ ((magdiam/2) - offset),0])
                MagHolder(stabb,magZB);
            translate([-(tableXY/2 + ((magdiam/2) - offset)),-((tableXY/2)+ ((magdiam/2) - offset)),0])
                MagHolder(stabb,magZB);
            translate([tableXY/2 + ((magdiam/2) - offset),-((tableXY/2)+ ((magdiam/2) - offset)),0])
                MagHolder(stabb,magZB);
                
            translate([0,0,4])        
                cube([tableXY,tableXY,8],true);
        }
        translate([0,0,5])
        MagnetBar3x();
        translate([-35,0,5])
        MagnetBar3x();
        translate([35,0,5])
        MagnetBar3x();
        
        translate([0,40,5])        
        rotate([0,0,90])
        MagnetBar3x();

        translate([0,-40,5])        
        rotate([0,0,90])
        MagnetBar3x();
    }
}
//TopTable();
//holepattern();
//Magnet30x5();
//MagHolder();
BottomTable();
//MagnetBar();
//alum();
//
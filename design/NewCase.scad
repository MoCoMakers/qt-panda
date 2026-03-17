cx = 100;
cy = 210; //130 + 40 + 40
cz = 50;
th = 4; // thickness of the walls

module caseBase()
{
    difference (){
    cube([cx,cy,cz],true);
    translate([0,0,th])
    cube([cx-th,cy-th,cz],true);
    }
}

caseBase();
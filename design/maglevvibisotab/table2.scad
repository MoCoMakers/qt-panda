sx = 25;
sy = 25;
sz = 5;
magZ = 4;

module mag1()
{
    cylinder(r=15/2,h=4,$fn =99);
}

module side()
{
    difference()
    {
    cube([sx,sy,sz],true);
    translate([0,0,sz/2 - magZ + .1])
    mag1();    
    }
}

module side3()
{
    side();
    translate([sx/2 - sz/2,0,-sx/2 + sz/2])
    rotate([0,90,0])
        side();
    translate([0,-sx/2 + sz/2,-sx/2 + sz/2])
        rotate([90,0,0])
            side();
}

module Socket3()
{
    rotate([0,180,0])
    side();

    translate([-(sx/2 - sz/2),0,-sx/2 + sz/2])
    rotate([0,90,0])
        side();
    translate([0,sx/2 - sz/2,-sx/2 + sz/2])
    rotate([90,0,0])
        side();

}

module RS3()
{
    translate([0,0,-15.75])
    rotate([45,-35.3,0])
    rotate([0,90,0])
    Socket3();
}

module RS3T()
{
    translate([0,0,-15.75])
    rotate([45,-35.3,0])
    rotate([-90,0,0])
    side3();
}

//side3();
spacing = 40;
module Bottom()
{
    difference()
    {
        union()
        {
            RS3();
            translate([0,spacing,0])
            RS3();
            translate([spacing,spacing,0])
            RS3();
            translate([spacing,0,0])
            RS3();
            translate([12,20,-2.5])
                cube([50,50,5],true);
        }   
        translate([-40,-30,-44])
            cube([100,100,20]);

    }
}

module Top()
{
union(){
    difference()
    {
        union()
        {
            RS3T();
            translate([0,spacing,0])
            RS3T();
            translate([spacing,spacing,0])
            RS3T();
            translate([spacing,0,0])
            RS3T();
        }   
        translate([-35,-40,-43])
            cube([100,100,20]);
    }
                translate([23,13,-24.5])
                cube([76,76,3],true);
    }
}
//Top();
//RS3T();
//translate([0,0,30])
Bottom();
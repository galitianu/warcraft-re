#include <vector>
#include <random>
#include <fstream>
#include <sstream>
#include <iostream>
// Diagnostic access only; links the unchanged wc3world. No state is written.
#define private public
#include "core/World.h"
#undef private
#include "Scenario.h"
int main(int argc, char** argv) {
 if(argc!=2) return 2;
 std::ifstream input(argv[1]); std::stringstream text; text<<input.rdbuf();
 auto s=scenario::parse(text.str()); wc3::World w(wc3::ModelVersion::v4);
 for(auto& u:s.units) {auto id=w.create_footman(u.position,u.facing); if(u.move_speed) w.set_move_speed(id,*u.move_speed);}
 std::size_t action=0; std::vector<bool> was(s.units.size(),false);
 for(unsigned step=0;step<=12000;++step) {
  while(action<s.actions.size() && s.actions[action].at_us==step*1000) {auto a=s.actions[action++]; w.issue_point_order(a.unit,wc3::order_move,a.point);}
  for(std::size_t i=0;i<s.units.size();++i) {
   bool partial=w.unit(i).route_partial_;
   if(partial!=was[i]) std::cout<<step<<","<<i<<","<<partial<<"\n";
   was[i]=partial;
  }
  if(step<12000) w.step();
 }
}

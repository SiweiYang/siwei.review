+ requirement
+ measure
+ design
  + stateless is good, but what about state
  + hotspot
  + re-provision time
+ dimension


+ in general, dumb components, smart orchastrating
  + component easy to test, integration can be hard
  + typically useful when services are provided in various packages
  + needs messaging, sometimes protocol needs designing
  + shared storage
+ how much control? we can trade control for productivity
+ should some components be treated differently
+ 12 factor, but with tradeoff
  + config injection is almost always necessary
+ start thinking early e.g. scaling, but iterate over the design


+ security
  + regular rotation
  + maybe there's trails for audit
  + isolation


+ capacity planning
  + leave margin of err and refine with iterations
  + initial load v.s. stable load
  + os and hardware can make a difference
  + pricing of different instance types
  + pricing of traffic: ingress, egress, between zones, between regions
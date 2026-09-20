// Run from the repository root: higgsedit build scripts/jev-welcome.jsx
const track = (property, points) => ({
  property, keyframes: points.map(([at, value, easing = "ease-in-out"]) => ({at, value, easing}))
});
const duration = 7;
const eyeX = x => (x - 112) * 0.32;
const eyeY = y => (y - 64) * 0.32;

function eye(cx, cy, wink) {
  const close = wink
    ? [[0,1],[1.02,1],[1.1,0.06],[1.21,1],[4.55,1],[4.72,0.05],[5.15,0.05],[5.34,1],[7,1]]
    : [[0,1],[1.02,1],[1.1,0.06],[1.21,1],[7,1]];
  const visible = wink
    ? [[0,1],[4.63,1],[4.72,0],[5.15,0],[5.27,1],[7,1]]
    : [[0,1],[7,1]];
  return <frame x={eyeX(cx)-15} y={eyeY(cy)-16} width={30} height={32} origin="center" layout="none"
    animate={[track("scaleY",close),track("opacity",visible)]}>
    <rect x={0} y={0} width={30} height={32} radius={15} fill="#fff3d6"/>
    <frame x={8} y={8} width={14} height={17} layout="none" animate={[
      track("offsetX",[[0,3],[0.5,3],[0.85,5],[1.18,-5],[1.5,-5],[2.6,4],[3.35,4],[3.85,0],[7,0]]),
      track("offsetY",[[0,-3],[0.8,-3],[1.2,0],[2.6,-2],[3.35,-2],[3.85,1],[7,1]])
    ]}>
      <rect x={0} y={0} width={14} height={17} radius={7} fill="#0e192f"/>
      <rect x={3} y={2} width={4} height={4} radius={2} fill="#ffffff"/>
    </frame>
  </frame>;
}

export default async ({project}) => {
  const p = await project({dir:"build/jev-welcome-animation",size:"800x340",fps:25,background:"#0d1423"});
  const buddy = await p.add("docs/assets/jev-character.png");
  const star = await p.add("docs/assets/jev-star.png");
  // Pop in, miss the landing, catch the balance, then turn into the final pose.
  // Squash on contact and stretch on recovery give the character a little weight.
  const entrance = [
    track("offsetX",[[0,-140],[0.42,-40],[0.68,-10],[0.95,25],[1.18,13],[1.42,-16],[1.65,-22],[2.1,-22],[2.5,-16],[2.83,5],[3.06,-3],[3.3,0],[7,0]]),
    track("offsetY",[[0,330],[0.3,38],[0.45,15],[0.65,-14],[0.96,14],[1.16,-8],[1.42,17],[1.65,-2],[2.1,-14],[2.46,-8],[2.8,14],[2.99,-5],[3.18,3],[3.36,0],[6.45,0],[6.95,330]]),
    // Keep 360 as the resting angle so the finishing wobble never unwinds the turn.
    track("rotation",[[0,-28],[0.43,-12],[0.68,8],[0.97,24],[1.18,7],[1.43,-21],[1.65,0,"ease-in"],[1.94,85,"linear"],[2.2,190,"linear"],[2.46,292,"ease-out"],[2.81,369],[3.05,354],[3.32,360],[4.55,360],[4.85,355],[5.4,360],[7,360]]),
    track("scaleX",[[0,0.65],[0.3,0.89],[0.45,1.12],[0.65,0.95],[0.96,1.08],[1.16,0.96],[1.43,1.1],[1.67,0.83],[2.12,0.78],[2.46,0.83],[2.81,1.12],[3.0,0.96],[3.32,1],[6.45,1],[6.95,0.65]]),
    track("scaleY",[[0,0.78],[0.3,1.07],[0.45,0.82],[0.65,1.04],[0.96,0.9],[1.16,1.03],[1.43,0.84],[1.67,0.94],[2.12,0.78],[2.46,0.91],[2.81,0.86],[3.0,1.04],[3.32,1],[6.45,1],[6.95,0.78]])
  ];
  p.compose([
    <text x={318} y={69} width={430} height={30} fontFamily="Montserrat" fontSize={15} fontWeight={600} letterSpacing={3} color="#8ae2ba">WELCOME TO THE EXPERIMENT</text>,
    <text x={315} y={109} width={440} height={50} fontFamily="Montserrat" fontSize={32} fontWeight={500} color="#f7efd9">This is</text>,
    <text x={313} y={152} width={455} height={65} fontFamily="Montserrat" fontSize={45} fontWeight={800} color="#f7efd9" animate={[
      track("opacity",[[0,0],[2.75,0],[3.3,1],[7,1]]),
      track("offsetY",[[0,14],[2.75,14],[3.3,0],[7,0]])
    ]}>Jev Workbench.</text>,
    <text x={317} y={233} width={450} height={36} fontFamily="Montserrat" fontSize={17} fontWeight={500} color="#b6c1d2">Tinker. Try things. Have a little fun.</text>,
    <rect x={318} y={215} width={68} height={4} fill="#ff6c40" radius={2}/>,
    <rect x={95} y={281} width={140} height={10} radius={5} fill="#030812" animate={[
      track("opacity",[[0,0],[0.3,0],[0.45,0.35],[1.43,0.35],[1.7,0.16],[2.46,0.16],[2.81,0.4],[3.32,0.23],[6.45,0.23],[6.95,0]]),
      track("scaleX",[[0,0.4],[0.45,1.1],[0.65,0.8],[0.96,1],[1.43,1.1],[1.7,0.65],[2.46,0.65],[2.81,1.15],[3.32,1],[7,1]])
    ]}/>,
    <frame x={37} y={14} width={256} height={307.2} origin="center" layout="none" animate={entrance}>
      <media file={buddy} x={0} y={0} width={256} height={307.2} fit="contain"/>
      {eye(453,482,false)}
      {eye(657,458,true)}
      <path d="M 0 10 Q 14 -2 28 10" x={eyeX(657)-14} y={eyeY(458)-5} width={28} height={12}
        stroke={{color:"#fff3d6",width:4,cap:"round"}} animate={[
          track("opacity",[[0,0],[4.63,0],[4.72,1],[5.15,1],[5.27,0],[7,0]])
        ]}/>
    </frame>,
    <media file={star} x={249} y={38} width={43} height={43} fit="contain" animate={[
      track("opacity",[[0,0],[4.65,0],[4.78,1],[6.45,1],[6.95,0]]),
      track("scale",[[0,0.05],[4.65,0.05],[4.86,1.35],[5.1,1],[6.45,1],[6.95,0.05]]),
      track("rotation",[[0,-25],[4.65,-25],[4.95,12],[5.2,0],[7,0]])
    ]}/>
  ],{dur:duration,name:"Character greeting"});
  p.compose(<rect x={0} y={0} width={800} height={340} fill="#0d1423" animate={[
    track("opacity",[[0,0],[6.45,0],[6.95,1],[7,1]])
  ]}/>,{dur:duration,name:"Loop reset"});
  await p.frame(4.92,"renders/jev-welcome.png");
  await p.render("renders/jev-welcome.mp4",{concurrency:2,shards:2});
};

// Run from the repository root: higgsedit build scripts/jev-welcome-spin.jsx
const track = (property, points) => ({
  property, keyframes: points.map(([at, value, easing = "ease-in-out"]) => ({at, value, easing}))
});
const duration = 6;
const eyeX = x => (x - 112) * 0.32;
const eyeY = y => (y - 64) * 0.32;

function eye(cx, cy, wink) {
  const close = wink
    ? [[0,1],[1.02,1],[1.1,0.06],[1.21,1],[3.55,1],[3.72,0.05],[4.15,0.05],[4.34,1],[6,1]]
    : [[0,1],[1.02,1],[1.1,0.06],[1.21,1],[6,1]];
  const visible = wink
    ? [[0,1],[3.63,1],[3.72,0],[4.15,0],[4.27,1],[6,1]]
    : [[0,1],[6,1]];
  return <frame x={eyeX(cx)-15} y={eyeY(cy)-16} width={30} height={32} origin="center" layout="none"
    animate={[track("scaleY",close),track("opacity",visible)]}>
    <rect x={0} y={0} width={30} height={32} radius={15} fill="#fff3d6"/>
    <frame x={8} y={8} width={14} height={17} layout="none" animate={[
      track("offsetX",[[0,3],[0.5,3],[0.85,5],[1.18,-5],[1.5,-5],[1.9,4],[2.3,4],[2.8,0],[6,0]]),
      track("offsetY",[[0,-3],[0.8,-3],[1.2,0],[1.9,-2],[2.3,-2],[2.8,1],[6,1]])
    ]}>
      <rect x={0} y={0} width={14} height={17} radius={7} fill="#0e192f"/>
      <rect x={3} y={2} width={4} height={4} radius={2} fill="#ffffff"/>
    </frame>
  </frame>;
}

export default async ({project}) => {
  const p = await project({dir:"build/jev-welcome-spin",size:"800x340",fps:25,background:"#0d1423"});
  const buddy = await p.add("docs/assets/jev-character.png");
  const star = await p.add("docs/assets/jev-star.png");
  // One continuous spinning arrival; a gentle settle, then the shared wink.
  const entrance = [
    track("offsetX",[[0,-80],[0.3,-38],[0.6,-22],[1.1,-16],[1.6,-6],[1.9,2],[2.2,0],[6,0]]),
    track("offsetY",[[0,280],[0.3,65],[0.55,0],[0.9,-10],[1.4,-5],[1.8,6],[2.1,-2],[2.3,0],[5.45,0],[5.95,330]]),
    track("rotation",[[0,-55,"linear"],[0.3,0,"linear"],[0.65,80,"linear"],[1.0,175,"linear"],[1.35,270,"ease-out"],[1.85,365],[2.12,358],[2.3,360],[3.55,360],[3.85,355],[4.4,360],[6,360]]),
    track("scaleX",[[0,0.6],[0.35,0.75],[1.1,0.78],[1.6,0.9],[1.85,1.04],[2.3,1],[5.45,1],[5.95,0.65]]),
    track("scaleY",[[0,0.6],[0.35,0.75],[1.1,0.78],[1.6,0.9],[1.85,0.96],[2.3,1],[5.45,1],[5.95,0.78]])
  ];
  p.compose([
    <text x={318} y={69} width={430} height={30} fontFamily="Montserrat" fontSize={15} fontWeight={600} letterSpacing={3} color="#8ae2ba">WELCOME TO THE EXPERIMENT</text>,
    <text x={315} y={109} width={440} height={50} fontFamily="Montserrat" fontSize={32} fontWeight={500} color="#f7efd9">This is</text>,
    <text x={313} y={152} width={455} height={65} fontFamily="Montserrat" fontSize={45} fontWeight={800} color="#f7efd9" animate={[
      track("opacity",[[0,0],[1.85,0],[2.3,1],[6,1]]),
      track("offsetY",[[0,14],[1.85,14],[2.3,0],[6,0]])
    ]}>Jev Workbench.</text>,
    <text x={317} y={233} width={450} height={36} fontFamily="Montserrat" fontSize={17} fontWeight={500} color="#b6c1d2">Tinker. Try things. Have a little fun.</text>,
    <rect x={318} y={215} width={68} height={4} fill="#ff6c40" radius={2}/>,
    <rect x={95} y={281} width={140} height={10} radius={5} fill="#030812" animate={[
      track("opacity",[[0,0],[0.3,0],[0.55,0.16],[1.4,0.16],[1.85,0.3],[2.3,0.23],[5.45,0.23],[5.95,0]]),
      track("scaleX",[[0,0.4],[0.55,0.65],[1.4,0.65],[1.85,1.05],[2.3,1],[6,1]])
    ]}/>,
    <frame x={37} y={14} width={256} height={307.2} origin="center" layout="none" animate={entrance}>
      <media file={buddy} x={0} y={0} width={256} height={307.2} fit="contain"/>
      {eye(453,482,false)}
      {eye(657,458,true)}
      <path d="M 0 10 Q 14 -2 28 10" x={eyeX(657)-14} y={eyeY(458)-5} width={28} height={12}
        stroke={{color:"#fff3d6",width:4,cap:"round"}} animate={[
          track("opacity",[[0,0],[3.63,0],[3.72,1],[4.15,1],[4.27,0],[6,0]])
        ]}/>
    </frame>,
    <media file={star} x={249} y={38} width={43} height={43} fit="contain" animate={[
      track("opacity",[[0,0],[3.65,0],[3.78,1],[5.45,1],[5.95,0]]),
      track("scale",[[0,0.05],[3.65,0.05],[3.86,1.35],[4.1,1],[5.45,1],[5.95,0.05]]),
      track("rotation",[[0,-25],[3.65,-25],[3.95,12],[4.2,0],[6,0]])
    ]}/>
  ],{dur:duration,name:"Character greeting"});
  p.compose(<rect x={0} y={0} width={800} height={340} fill="#0d1423" animate={[
    track("opacity",[[0,0],[5.45,0],[5.95,1],[6,1]])
  ]}/>,{dur:duration,name:"Loop reset"});
  await p.frame(3.92,"renders/jev-welcome-spin.png");
  await p.render("renders/jev-welcome-spin.mp4",{concurrency:2,shards:2});
};

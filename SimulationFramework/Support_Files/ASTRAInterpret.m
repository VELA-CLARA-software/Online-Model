(* ::Package:: *)

(************************************************************************)
(* This file was generated automatically by the Mathematica front end.  *)
(* It contains Initialization cells from a Notebook file, which         *)
(* typically will have the same name as this file except ending in      *)
(* ".nb" instead of ".m".                                               *)
(*                                                                      *)
(* This file is intended to be loaded into the Mathematica kernel using *)
(* the package loading commands Get or Needs.  Doing so is equivalent   *)
(* to using the Evaluate Initialization Cells menu command in the front *)
(* end.                                                                 *)
(*                                                                      *)
(* DO NOT EDIT THIS FILE.  This entire file is regenerated              *)
(* automatically each time the parent Notebook file is saved in the     *)
(* Mathematica front end.  Any changes you make to this file will be    *)
(* overwritten.                                                         *)
(************************************************************************)



(* ::Input::Initialization:: *)
BeginPackage["ASTRAInterpreter`"]


(* ::Input::Initialization:: *)
Needs["h5mma`"]


(* ::Input::Initialization:: *)
ASTRAColumnsXemit = {{"z", Quantity["Meters"],Number}, {"t", Quantity["ns"],Number}, {"xavr", Quantity["mm"],Number}, {"xrms", Quantity["mm"],Number}, {"xprms", Quantity["mrad"],Number}, {"\[Epsilon]xnorm", Quantity[IndependentUnit["\[Pi]"]] Quantity["mm"] Quantity["mrad"],Number}, {"xxpavr", Quantity["mm"] Quantity["mrad"],Number}};


(* ::Input::Initialization:: *)
ASTRAColumnsYemit={{"z",Quantity["Meters"],Number},{"t",Quantity["ns"],Number},{"yavr",Quantity["mm"],Number},{"yrms",Quantity["mm"],Number},{"yprms",Quantity["mrad"],Number},{"\[Epsilon]ynorm",Quantity[IndependentUnit["\[Pi]"]] Quantity["mm"]Quantity["mrad"],Number},{"yypavr",Quantity["mm"]Quantity["mrad"],Number}};


(* ::Input::Initialization:: *)
ASTRAColumnsZemit={{"z",Quantity["Meters"],Number},{"t",Quantity["ns"],Number},{"Ekin",Quantity["MeV"],Number},{"zrms",Quantity["mm"],Number},{"\[CapitalDelta]Erms",Quantity["keV"],Number},{"\[Epsilon]znorm",Quantity[IndependentUnit["\[Pi]"]] Quantity["mm"]Quantity["keV"],Number},{"zEavr",Quantity["keV"],Number}};


(* ::Input::Initialization:: *)
ASTRAColumnsParticles={{"x",Quantity["Meters"],Number},{"y",Quantity["Meters"],Number},{"z",Quantity["Meters"],Number},{"px",Quantity["eV"]/Quantity["SpeedOfLight"],Number},{"py",Quantity["eV"]/Quantity["SpeedOfLight"],Number},{"pz",Quantity["eV"]/Quantity["SpeedOfLight"],Number},{"clock",Quantity["ns"],Number},{"charge",Quantity["nC"],Number},{"index",1,Number},{"status",1,Number}};


(* ::Input::Initialization:: *)
ASTRAXemitInterpret::usage="ASTRAXemitInterpret[file] interpret the ASTRA X-Emit file into Mathematica format."


(* ::Input::Initialization:: *)
ASTRAYemitInterpret::usage="ASTRAYemitInterpret[file] interpret the ASTRA Y-Emit file into Mathematica format."


(* ::Input::Initialization:: *)
ASTRAZemitInterpret::usage="ASTRAZemitInterpret[file] interpret the ASTRA Z-Emit file into Mathematica format."


(* ::Input::Initialization:: *)
ASTRAemitInterpret::usage="ASTRAemitInterpret[file] interpret the ASTRA Emit files into Mathematica format assuming the naming convention \"*[X/Y/Z]emit*\"."


(* ::Input::Initialization:: *)
ASTRAemitInterpretHDF5Summary::usage="ASTRAemitInterpretHDF5Summary[file] interpret the ASTRA Emit files into Mathematica format from an HDF5 ASTRA Summary file."


(* ::Input::Initialization:: *)
ASTRABeamInterpret::usage="ASTRABeamInterpret[file] interpret the ASTRA Paticle file into Mathematica format."


(* ::Input::Initialization:: *)
unitConversionRules = {"Nanoseconds" -> "ns", "Milliradians" -> "mrad", "Millimeters" -> "mm", "Megaelectronvolts" -> "MeV", "Kiloelectronvolts" -> "keV","Nanocoulombs"->"nC","Electronvolts"->"eV","Meters"->"m"}


(* ::Input::Initialization:: *)
Begin["`Private`"]


(* ::Input::Initialization:: *)
ASTRAemitInterpret::wrongFileType="Filename doesn't contain \"`1`emit\". Override with IgnoreFilename\[Rule]True"


(* ::Input::Initialization:: *)
ASTRAImportData[file_,columns_]:=Transpose[ReadList[file,columns[[All,-1]]]]


(* ::Input::Initialization:: *)
ASTRAImportData[files_List,columns_]:=Transpose[Join[Sequence@@Block[{file=#},
ReadList[file,columns[[All,-1]]]
]&/@files]]


(* ::Input::Initialization:: *)
ASTRAColumnsAssign[columns_,data_,opts___Rule]:=Block[{prefix,postfix,units},
prefix=Global`ASTRAPrefix/.{opts}/.{Global`ASTRAPrefix->""};
postfix=Global`ASTRAPostfix/.{opts}/.{Global`ASTRAPostfix->""};
units=Global`ASTRAUnits/.{opts}/.{Global`ASTRAUnits->False};
(Clear[Evaluate[prefix<>#[[1,1]]<>postfix]];
Evaluate[Symbol@Evaluate[prefix<>#[[1,1]]<>postfix]]=If[units,#[[1,2]],1]#[[2]])&/@Transpose[{columns,data}];
]


(* ::Input::Initialization:: *)
ASTRAPrintColumns[columns_,opts___Rule]:=Block[{prefix,postfix},
prefix=Global`ASTRAPrefix/.{opts}/.{Global`ASTRAPrefix->""};
postfix=Global`ASTRAPostfix/.{opts}/.{Global`ASTRAPostfix->""};
Print[StringReplace["Columns Redefined: "<>StringJoin@@MapIndexed[If[#2[[1]]>1,", ",""]<>prefix<>#[[1]]<>postfix<>" ["<>StringJoin@@MapIndexed[If[#2[[1]]>1," ",""]<>ToString[#]&,
Replace[
If[(cases=Cases[{QuantityUnit[#[[2]]]},Times[a_,Power["SpeedOfLight",b_]]:>a<>If[Sign[b]<0,"/"]<>ToString["c"<>If[Abs[b]=!=1,"^"<>ToString[Abs[b]],""]]])==={},
QuantityUnit[#[[2]]],
cases],IndependentUnit[a_]:>a,\[Infinity]]
]<>"]"&,columns],unitConversionRules]]
]


(* ::Input::Initialization:: *)
ASTRAXemitInterpret[file_String,opts___Rule]:=Block[{dataASTRAx,verbose,ignorefilename},
verbose=Global`ASTRAVerbose/.{opts}/.{Global`ASTRAVerbose->False};
ignorefilename=Global`IgnoreFilename/.{opts}/.{Global`IgnoreFilename->False};
If[!StringMatchQ[file,"*Xemit*"]&&!ignorefilename,
Message[ASTRAemitInterpret::wrongFileType,"X"],
dataASTRAx=ASTRAImportData[file,ASTRAColumnsXemit];
ASTRAColumnsAssign[ASTRAColumnsXemit,dataASTRAx,opts];
If[verbose,ASTRAPrintColumns[ASTRAColumnsXemit,opts]]
]
]


(* ::Input::Initialization:: *)
ASTRAXemitInterpret[{files__String},opts___Rule]:=Block[{dataASTRAx,verbose,ignorefilename},
verbose=Global`ASTRAVerbose/.{opts}/.{Global`ASTRAVerbose->False};
ignorefilename=Global`IgnoreFilename/.{opts}/.{Global`IgnoreFilename->False};
If[!(And@@(StringMatchQ[#,"*Xemit*"]&/@{files}))&&!ignorefilename,
Message[ASTRAemitInterpret::wrongFileType,"X"],
dataASTRAx=ASTRAImportData[{files},ASTRAColumnsXemit];
ASTRAColumnsAssign[ASTRAColumnsXemit,dataASTRAx,opts];
If[verbose,ASTRAPrintColumns[ASTRAColumnsXemit,opts]]
]
]


(* ::Input::Initialization:: *)
ASTRAXemitInterpret[data_List,opts___Rule]:=Block[{dataASTRAx,verbose,ignorefilename},
verbose=Global`ASTRAVerbose/.{opts}/.{Global`ASTRAVerbose->False};
ignorefilename=Global`IgnoreFilename/.{opts}/.{Global`IgnoreFilename->False};
dataASTRAx=Transpose[Join[Sequence@@data]];
ASTRAColumnsAssign[ASTRAColumnsXemit,dataASTRAx,opts];
If[verbose,ASTRAPrintColumns[ASTRAColumnsXemit,opts]]
]


(* ::Input::Initialization:: *)
ASTRAYemitInterpret[file_String,opts___Rule]:=Block[{dataASTRAy,verbose,ignorefilename},
verbose=Global`ASTRAVerbose/.{opts}/.{Global`ASTRAVerbose->False};
ignorefilename=Global`IgnoreFilename/.{opts}/.{Global`IgnoreFilename->False};
If[!StringMatchQ[file,"*Yemit*"]&&!ignorefilename,
Message[ASTRAemitInterpret::wrongFileType,"Y"],
dataASTRAy=ASTRAImportData[file,ASTRAColumnsYemit];
ASTRAColumnsAssign[ASTRAColumnsYemit,dataASTRAy,opts];
If[verbose,ASTRAPrintColumns[ASTRAColumnsYemit,opts]]
]
]


(* ::Input::Initialization:: *)
ASTRAYemitInterpret[data_List,opts___Rule]:=Block[{dataASTRAy,verbose,ignorefilename},
verbose=Global`ASTRAVerbose/.{opts}/.{Global`ASTRAVerbose->False};
ignorefilename=Global`IgnoreFilename/.{opts}/.{Global`IgnoreFilename->False};
dataASTRAy=Transpose[Join[Sequence@@data]];
ASTRAColumnsAssign[ASTRAColumnsYemit,dataASTRAy,opts];
If[verbose,ASTRAPrintColumns[ASTRAColumnsYemit,opts]]
]


(* ::Input::Initialization:: *)
ASTRAYemitInterpret[{files__String},opts___Rule]:=Block[{dataASTRAy,verbose,ignorefilename},
verbose=Global`ASTRAVerbose/.{opts}/.{Global`ASTRAVerbose->False};
ignorefilename=Global`IgnoreFilename/.{opts}/.{Global`IgnoreFilename->False};
If[!(And@@(StringMatchQ[#,"*Yemit*"]&/@{files}))&&!ignorefilename,
Message[ASTRAemitInterpret::wrongFileType,"Y"],
dataASTRAy=ASTRAImportData[{files},ASTRAColumnsYemit];
ASTRAColumnsAssign[ASTRAColumnsYemit,dataASTRAy,opts];
If[verbose,ASTRAPrintColumns[ASTRAColumnsYemit,opts]]
]
]


(* ::Input::Initialization:: *)
ASTRAZemitInterpret[file_String,opts___Rule]:=Block[{dataASTRAz,verbose,ignorefilename},
verbose=Global`ASTRAVerbose/.{opts}/.{Global`ASTRAVerbose->False};
ignorefilename=Global`IgnoreFilename/.{opts}/.{Global`IgnoreFilename->False};
If[!StringMatchQ[file,"*Zemit*"]&&!ignorefilename,
Message[ASTRAemitInterpret::wrongFileType,"Z"],
dataASTRAz=ASTRAImportData[file,ASTRAColumnsZemit];
ASTRAColumnsAssign[ASTRAColumnsZemit,dataASTRAz,opts];
If[verbose,ASTRAPrintColumns[ASTRAColumnsZemit,opts]]
]
]


(* ::Input::Initialization:: *)
ASTRAZemitInterpret[data_List,opts___Rule]:=Block[{dataASTRAz,verbose,ignorefilename},
verbose=Global`ASTRAVerbose/.{opts}/.{Global`ASTRAVerbose->False};
ignorefilename=Global`IgnoreFilename/.{opts}/.{Global`IgnoreFilename->False};
dataASTRAz=Transpose[Join[Sequence@@data]];
ASTRAColumnsAssign[ASTRAColumnsZemit,dataASTRAz,opts];
If[verbose,ASTRAPrintColumns[ASTRAColumnsZemit,opts]]
]


(* ::Input::Initialization:: *)
ASTRAZemitInterpret[{files__String},opts___Rule]:=Block[{dataASTRAz,verbose,ignorefilename},
verbose=Global`ASTRAVerbose/.{opts}/.{Global`ASTRAVerbose->False};
ignorefilename=Global`IgnoreFilename/.{opts}/.{Global`IgnoreFilename->False};
If[!(And@@(StringMatchQ[#,"*Zemit*"]&/@{files}))&&!ignorefilename,
Message[ASTRAemitInterpret::wrongFileType,"Z"],
dataASTRAz=ASTRAImportData[{files},ASTRAColumnsZemit];
ASTRAColumnsAssign[ASTRAColumnsZemit,dataASTRAz,opts];
If[verbose,ASTRAPrintColumns[ASTRAColumnsZemit,opts]]
]
]


(* ::Input::Initialization:: *)
ASTRAemitInterpret[file_String,opts___Rule]:=Block[{},
ASTRAXemitInterpret[StringReplace[file,{"Yemit"->"Xemit","Zemit"->"Xemit"}],opts];
ASTRAYemitInterpret[StringReplace[file,{"Xemit"->"Yemit","Zemit"->"Yemit"}],opts];
ASTRAZemitInterpret[StringReplace[file,{"Xemit"->"Zemit","Yemit"->"Zemit"}],opts];
]


(* ::Input::Initialization:: *)
ASTRAemitInterpret[{files__String},opts___Rule]:=Block[{},
ASTRAXemitInterpret[StringReplace[{files},{"Yemit"->"Xemit","Zemit"->"Xemit"}],opts];
ASTRAYemitInterpret[StringReplace[{files},{"Xemit"->"Yemit","Zemit"->"Yemit"}],opts];
ASTRAZemitInterpret[StringReplace[{files},{"Xemit"->"Zemit","Yemit"->"Zemit"}],opts];
]


(* ::Input::Initialization:: *)
ASTRAemitInterpret[datax_List,datay_List,dataz_List,opts___Rule]:=Block[{},
ASTRAXemitInterpret[datax,opts];
ASTRAYemitInterpret[datay,opts];
ASTRAZemitInterpret[dataz,opts];
]


(* ::Input::Initialization:: *)
ASTRAemitInterpretHDF5Summary[file_String,opts___Rule]:=Block[{datax,datay,dataz},
datax=ImportHDF5[file,{"Datasets",Select[ImportHDF5[file],StringMatchQ[#,"/Xemit/*"]&]}];
datay=ImportHDF5[file,{"Datasets",Select[ImportHDF5[file],StringMatchQ[#,"/Yemit/*"]&]}];
dataz=ImportHDF5[file,{"Datasets",Select[ImportHDF5[file],StringMatchQ[#,"/Zemit/*"]&]}];
ASTRAXemitInterpret[datax,opts];
ASTRAYemitInterpret[datay,opts];
ASTRAZemitInterpret[dataz,opts];
]


(* ::Input::Initialization:: *)
ASTRAemitInterpretHDF5Summary[{files__String},opts___Rule]:=Block[{datax,datay,dataz},
datax=Join@@(ImportHDF5[#,{"Datasets",Select[ImportHDF5[#],StringMatchQ[#,"/Xemit/*"]&]}]&/@{files});
datay=Join@@(ImportHDF5[#,{"Datasets",Select[ImportHDF5[#],StringMatchQ[#,"/Yemit/*"]&]}]&/@{files});
dataz=Join@@(ImportHDF5[#,{"Datasets",Select[ImportHDF5[#],StringMatchQ[#,"/Zemit/*"]&]}]&/@{files});
ASTRAXemitInterpret[datax,opts];
ASTRAYemitInterpret[datay,opts];
ASTRAZemitInterpret[dataz,opts];
]


(* ::Input::Initialization:: *)
ASTRABeamInterpret[file_,opts___Rule]:=Block[{dataASTRAbeam,verbose,normalise,ignorefilename},
verbose=Global`ASTRAVerbose/.{opts}/.{Global`ASTRAVerbose->False};
normalise=Global`ASTRANormalise/.{opts}/.{Global`ASTRANormalise->True};
prefix=Global`ASTRAPrefix/.{opts}/.{Global`ASTRAPrefix->""};
postfix=Global`ASTRAPostfix/.{opts}/.{Global`ASTRAPostfix->""};
dataASTRAbeam=ASTRAImportData[file,ASTRAColumnsParticles];
ASTRAColumnsAssign[ASTRAColumnsParticles,dataASTRAbeam,opts];
If[normalise==True,
ToExpression["Global`"<>prefix<>"z"<>postfix<>"[[2;;-1]]=Rest[Global`"<>prefix<>"z"<>postfix<>"]+First[Global`"<>prefix<>"z"<>postfix<>"]"];
ToExpression["Global`"<>prefix<>"pz"<>postfix<>"[[2;;-1]]=Rest[Global`"<>prefix<>"pz"<>postfix<>"]+First[Global`"<>prefix<>"pz"<>postfix<>"]"]
];
If[verbose,ASTRAPrintColumns[ASTRAColumnsParticles,opts]]
]


(* ::Input::Initialization:: *)
End[]


(* ::Input::Initialization:: *)
EndPackage[]




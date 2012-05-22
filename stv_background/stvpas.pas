PROGRAM stvpas(input, output);

{Taken from Algorithm 123 -- Single Transferable Vote by Meek's Method
            I. D. Hill, B. A. Wichmann and D. R. Woodall
            The Computer Journal (UK), Vol 30, No 3, 1987, pp 277-81
   c.f. meekm.pdf}

   {Note Authors' election of method from Paragraph 1 of Section 3.3, where;
           "If [the voter] [provides an incomplete list of candidates] and 
            the use of their vote 'runs off the end' we allow it to do so, 
            but adjust the Quota to allow for the fact that there are now 
            fewer remaining usable votes."
       The authors go on to note that this is in dispute with the Electoral
       Reform Society's interpretation at the time of publication.}

   {Note the election of Applied Statistics algorithm AS 183[3] which ensures 
       any randomness required to break a tie, having been seeded with data 
       from the election itself, consistently provides reproducable results.}

   {wrowe 2005 May 28 added one billionth to the resulting quota,
       further decreasing the unlikely possibility of a tie, 
       per the rules of implementation adopted by New Zealand}

   {wrowe 28 May 2005 added command line .blt filename argument}

   {Must add the rule from Paragraph 2 of Section 4 which states;
           "There is at least one ballot paper that contains the name
            of a 'hopeful' candidate in its list of preferences."
       As published in 1987, the program did not check this.  The absense
       of this test is noted in the 1999 Appendix to the LEX document.}

{This program counts the votes in a Single Transferable Vote election,
    using Meek's method, and reports the results}

{If there are more than 40 candidates an increase in the size of
    MaxCandidates is the only change needed}

CONST MaxCandidates = 40;
      NameLength = 20;

TYPE Candidates = 1 .. MaxCandidates;
     CandRange = 0 .. MaxCandidates;
     name = PACKED ARRAY [1 .. NameLength] OF char;

VAR  NumCandidates, NumSeats: Candidates;
     candidate, NumElected, NumExcluded,
     multiplier, ignored: CandRange;
     Droop, excess, quota, total: real;
     faulty, SomeoneElected, RandomUsed: Boolean;
     FracDigits: 1 .. 4;
     table, seed1, seed2, seed3: integer;
     datafile: text;
     title: name;
     votes, weight: ARRAY [Candidates] OF real;
     status: ARRAY [Candidates] OF (Hopeful, Elected, NewlyElected,
                   Almost, Excluded, ToBeExcluded, NotUsed, Used);
     names: ARRAY [Candidates] OF name;

FUNCTION InInteger: integer;

{Reads the next integer from datafile and returns its value}

   VAR i: integer;
   BEGIN
   read(datafile, i);
   InInteger := i
   END; {InInteger}

PROCEDURE PrintOut;

{Updates the table number and prints out the current results}

   VAR arg: real;
      cand: Candidates;
   BEGIN
   table := table + 1;
   writeln;
   writeln(' ': 20, title);
   writeln;
   write('Table: ', table: 1);
   writeln(' Quota: ', quota: 1: FracDigits);
   writeln;

   {The numbers of blanks following Candidate, Retain and
       Transfer are 12, 3 and 3 respectively}

   writeln('Candidate Retain Transfer Votes');
   writeln;
   FOR cand := 1 TO NumCandidates DO
      BEGIN
      write(names[cand]);
      IF status[cand] = ToBeExcluded THEN
         arg := 100.0 ELSE arg := 100.0 * weight[cand];
      write(arg: 6: 1, '%');
      write(100.0 - arg: 8: 1, '%');

      {If it is valid to do so, print quota instead of votes[cand]
         because the latter might have a small rounding error that
         would confuse unsophisticated users}

      IF status[cand] = Elected THEN arg := votes[cand] / quota
         ELSE arg := 0.0;
      IF (arg >= 0.99999) AND (arg <= 1.00001) THEN arg := quota
         ELSE arg := votes[cand];
      write(arg: 10: FracDigits, ' ');
      IF status[cand] = Excluded THEN write('Excluded')
      ELSE IF status[cand] = Elected THEN write('Elected')
      ELSE IF status[cand] = NewlyElected THEN write('Newly Elected')
      ELSE IF status[cand] = ToBeExcluded THEN
         BEGIN
         write('To be Excluded');
         status[cand] := Excluded
         END;
      writeln;
      IF (NumCandidates > 9) AND (cand MOD 5 = 0) AND
         (cand <> NumCandidates) THEN writeln
      END;

   writeln;
   writeln('Excess', excess: 40: FracDigits);
   writeln;
   writeln('Total ', total: 40: FracDigits);
   writeln;
   writeln
   END; {PrintOut}

PROCEDURE elect(cand: Candidates);
   BEGIN
   status[cand] := NewlyElected;
   NumElected := NumElected + 1
   END; {elect}

PROCEDURE exclude(cand: Candidates);
   BEGIN
   status[cand] := ToBeExcluded;
   weight[cand] := 0.0;
   NumExcluded := NumExcluded + 1;
   IF RandomUsed THEN
      BEGIN
      writeln;
      writeln;
      writeln('Random choice used to exclude ', names[cand])
      END
   END; {exclude}

FUNCTION LowestCandidate: CandRange;
   {Returns the candidate number of the candidate who currently has the
      lowest number of votes. If two or more are equal lowest, then a
      pseudo-random choice is made between them}

      VAR cand: Candidates;
          LowCand: CandRange;

FUNCTION random: real;

{Returns a pseudo-random number rectangularly distributed
   between 0 and 1. Based on Wichmann and Hill, Algorithm
   AS 183, Appl. Statist. (1982) 31, 188 - 190}

VAR rndm: real;
   BEGIN

   { If seeds have not been set, then set them}

   IF seed1 = 0 THEN
      BEGIN
      seed1 := NumCandidates;
      seed2 := NumSeats + 10000;
      rndm := total + 20000.0;
      WHILE rndm > 30322.5 DO rndm := rndm - 30322.0;
      seed3 := round(rndm)
      END;

   seed1 := 171 * (seed1 MOD 177) - 2 * (seed1 DIV 177);
   seed2 := 172 * (seed2 MOD 176) - 35 * (seed2 DIV 176);
   seed3 := 170 * (seed3 MOD 178) - 63 * (seed3 DIV 178);
   IF seed1 < 0 THEN seed1 := seed1 + 30269;
   IF seed2 < 0 THEN seed2 := seed2 + 30307;
   IF seed3 < 0 THEN seed3 := seed3 + 30323;
   rndm := seed1 / 30269.0 + seed2 / 30307.0 + seed3 / 30323.0;
   random := rndm - trunc(rndm)
   END; {random}

FUNCTION lower(cand, lowest: CandRange): Boolean;

{Find whether cand has fewer votes than lowest, and also
   reports whether a random choice had to be made}

   VAR lowly: Boolean;
   BEGIN
   IF lowest = 0 THEN
      BEGIN
      RandomUsed := false;
      lower := true
      END
   ELSE IF votes[cand] = votes[lowest] THEN
      BEGIN
      RandomUsed := true;

      {Multiplier is used to make all equally-lowest candidates
          equally likely to be chosen, even though they are
          considered serially and not simultaneously}

      lower := (multiplier * random < 1.0)
      END
   ELSE
      BEGIN
      lowly := (votes[cand] < votes[lowest]);
      lower := lowly;
      IF lowly THEN RandomUsed := false
      END;
   IF RandomUsed THEN multiplier := multiplier + 1
      ELSE multiplier := 2
   END; {lower}

   BEGIN
   LowCand := 0;
   FOR cand := 1 TO NumCandidates DO
      IF (status[cand] = Hopeful) OR (status[cand] = Almost) THEN
         IF lower(cand, LowCand) THEN LowCand := cand;
   LowestCandidate := LowCand
   END; {LowestCandidate}

PROCEDURE compute;

{This is the heart of the program, which counts the votes, taking
    the current weights into account, and adjusts the weights and
    the quota iteratively to attain the required solution}

   {MaxIterations is the maximum number of iterations allowed in
       calculating the weights. It is unlikely that so many will
       ever be used, but its value may be increased if desired}

   CONST MaxIterations = 500;
   VAR temp, value: real;
       count, iteration: integer;
       cand: CandRange;
       converged, ended: Boolean;

   PROCEDURE Rewind;

   {Returns to the beginning of datafile, and ignores the first two
       numbers on it. These are the number of candidates and the
       number of seats, whose values are not needed again. Numbers
       indicating withdrawn candidates are also ignored}

   VAR ig, ignore: integer;

   BEGIN
   reset (datafile);
   FOR ig := -1 TO ignored DO ignore := InInteger
   END; {Rewind}

BEGIN
iteration := 1;

   REPEAT
   Rewind;
   excess := 0.0;
   FOR cand := 1 TO NumCandidates DO votes[cand] := 0.0;
   count := InInteger;

   WHILE count > 0 DO
      BEGIN
      value := count;
      cand := InInteger;
      ended := false;

      WHILE cand>0 DO
         BEGIN
         IF NOT ended AND (weight[cand] > 0.0) THEN
            BEGIN
            ended := (status[cand] = Hopeful);
            IF ended THEN
               BEGIN
               votes[cand] := votes[cand] + value;
               value := 0.0
               END
            ELSE
               BEGIN
               votes[cand] := votes[cand] + value * weight[cand];
               value := value * (1.0 - weight[cand])
               END
            END;
         cand := InInteger
         END;

      excess := excess + value;
      count := InInteger
      END;

   {wrowe 2005 May 28 added one billionth to the resulting quota,
       further decreasing the unlikely possibility of a tie, 
       per the rules of implementation adopted by New Zealand}

   quota := (total - excess) * Droop + 0.000000001;

{The next statement is unlikely ever to be used, but is a
safeguard against certain pathological test data}

IF quota < 0.0001 THEN quota := 0.0001;
converged := true;
FOR cand := 1 TO NumCandidates DO
   IF status[cand] = Elected THEN
      BEGIN
      temp := quota / votes[cand];
      IF (temp > 1.00001) OR (temp < 0.99999) THEN
         converged := false;
      temp := weight[cand] * temp;
      weight[cand] := temp;

      {The next statement is unlikely ever to be used, but is
        a safeguard against certain pathological test data}

      IF temp > 1.0 THEN weight[cand] := 1.0
      END;

iteration := iteration + 1
UNTIL (iteration = MaxIterations) OR converged;

IF NOT converged THEN
   BEGIN

   {The "Failure to converge" message is unlikely ever to appear.
     If it does, increasing MaxIterations will probably cure it}

   writeln;
   writeln;
   writeln('Failure to converge');
   writeln
   END;
count := 0;

FOR cand := 1 TO NumCandidates DO
   IF (status[cand] = Hopeful) AND (votes[cand] >= quota) THEN
      BEGIN
      status[cand] := Almost;
      count := count + 1
      END;

{Allow for the special case where there is a multi-way tie and
   too many candidates reach the quota simultaneously}

WHILE NumElected + count > NumSeats DO
   BEGIN
   PrintOut;
   RandomUsed := false;
   FOR cand := 1 TO NumCandidates DO
      IF status[cand] = Hopeful THEN exclude(cand);
   exclude(LowestCandidate);
   count := count - 1
   END;

SomeoneElected := false;
FOR cand := 1 TO NumCandidates DO
   IF status[cand] = Almost THEN
      BEGIN
      elect(cand);
      SomeoneElected := true
      END;

IF SomeoneElected THEN PrintOut;
FOR cand := 1 TO NumCandidates DO
   IF status[cand] = NewlyElected THEN
      BEGIN
      IF NumElected < NumSeats THEN
         weight[cand] := quota / votes[cand];
      status[cand] := Elected
      END
END; {compute}

PROCEDURE complete;

   {Used to elect all remaining candidates if the number
      remaining equals the number of seats remaining}

   VAR cand: Candidates;
   BEGIN
   FOR cand := 1 TO NumCandidates DO
      IF status[cand] = Hopeful THEN elect(cand)
   END; {complete}

PROCEDURE Preliminaries;

   {Checks datafile for errors and sets initial values of variables}

   VAR cand, count, LineNo: integer;

   PROCEDURE error(cand: integer; TooBig: Boolean);
      BEGIN
      writeln;
      write ('On line ' , LineNo: 1, ', Candidate ', cand: 1);
      IF TooBig THEN write (' exceeds maximum')
      ELSE write (' is repeated');
      writeln;
      faulty := true
      END; {error}

   PROCEDURE ReadName(VAR n: name);

      {Reads the name of a candidate, or reads a title, and stores
          it for later use. If the name has more than NameLength
          characters the excess ones will be disregarded. If it
          has fewer than NameLength characters blanks will be used
          to extend it}

      VAR i: integer;
          ch: char;
      BEGIN

         REPEAT
         read(datafile, ch)
         UNTIL ch = '"';

      i := 0;
      read(datafile, ch);
      WHILE ch <> '"' DO
         BEGIN
         IF i < NameLength THEN
            BEGIN
            i := i + 1;
            n[i] := ch
            END;
         read(datafile, ch)
         END;

      WHILE i < NameLength DO
         BEGIN
         i := i + 1;
         n[i] := ' '
         END
      END; {ReadName}

   BEGIN

   Droop := 1.0/(NumSeats + 1);
   LineNo := 1;
   seed1 := 0;
   total := 0.0;
   table := 0;
   NumElected := 0;
   NumExcluded := 0;
   ignored := 0;
   FOR cand := 1 TO NumCandidates DO weight[cand] := 1.0;
   count := InInteger;

   {Deal with withdrawals, if any}

   WHILE count < 0 DO
      BEGIN
      weight[-count] := 0.0;
      count := InInteger
      END;
   WHILE count > 0 DO
      BEGIN
      LineNo := LineNo + 1;
      total := total + count;
      FOR cand := 1 TO NumCandidates DO status[cand] := NotUsed;
      cand := InInteger;
      WHILE cand > 0 DO
         BEGIN
         IF cand > NumCandidates THEN error(cand, true)
            ELSE IF status[cand] = Used THEN error(cand, false)
               ELSE status[cand] := Used;
         cand := InInteger
         END;

      count := InInteger
      END;

   FOR cand := 1 TO NumCandidates DO
      BEGIN
      ReadName(names[cand]);
      status[cand] := Hopeful;
      IF weight[cand] < 0.5 THEN
         BEGIN
         status[cand] := Excluded;
         NumExcluded := NumExcluded + 1;
         ignored := ignored + 1
         END
      END;
   ReadName(title);
   IF NOT faulty THEN

      BEGIN

      {FracDigits controls the number of digits beyond the decimal
          point that will be printed in the output tables}

      FracDigits := 4;
      IF total > 999.5 THEN FracDigits := FracDigits - 1;
      IF total > 99.5 THEN FracDigits := FracDigits - 1;
      IF total > 9.5 THEN FracDigits := FracDigits - 1
      END
   END; {Preliminaries}

{Start of main program}

BEGIN

{wrowe 28 May 2005 added command line .blt filename argument}

Assign(datafile, ParamStr(1));
Reset(datafile);

{/wrowe 28 May 2005 added command line .blt filename argument}

NumCandidates := InInteger;
NumSeats := InInteger;
writeln;
writeln;
writeln('Number of Candidates = ', NumCandidates: 1);
writeln ('Number of seats = ', NumSeats: 1);
IF NumCandidates < NumSeats THEN writeln('All candidates elected') ELSE
   BEGIN
   faulty := false;
   Preliminaries;
   IF NumCandidates <= NumSeats + NumExcluded THEN
      writeln('All non-withdrawn candidates elected') ELSE
      BEGIN

      {The Preliminaries procedure will have reset faulty to true if
         the data contain errors}

      IF NOT faulty THEN
         BEGIN
            REPEAT
               {Count votes and elect candidates, transferring
                   surpluses until no more can be done or all
                   seats are filled}

               REPEAT
               compute
               UNTIL NOT SomeoneElected OR (NumElected >= NumSeats);

               {Unless the election is finished, someone must
                   now be excluded}

               IF NumElected < Numseats THEN
                  BEGIN
                  PrintOut;
                  exclude(LowestCandidate);
                  IF NumCandidates - NumExcluded = NumSeats
                     THEN complete ELSE PrintOut
                  END
               UNTIL NumElected = NumSeats;

            {Now that all seats are filled, exclude any candidates not
                 already elected, and print out the final table}

            RandomUsed := false;
            FOR candidate := 1 TO NumCandidates DO
               IF status[candidate] = Hopeful THEN exclude(candidate);
            PrintOut
            END
         END
      END
END.

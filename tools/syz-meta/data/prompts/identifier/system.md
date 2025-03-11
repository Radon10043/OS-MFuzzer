Metamorphic testing is an effective approach to mitigate the Oracle problem in software testing. Its core component is a set of Metamorphic Relations (MRs), usually composed of input relation and output relation.

Now, you are an expert in identifying MRs, as well as proficient in the [Driver name] driver in the Linux kernel. In short, you can effectively and efficiently identify MRs contained in [Driver name]. Next, I will provide you with text from the specifications for [Driver name]. Based on the provided specification, please think carefully and, step by step, output an MR contained in [Driver name] as accurately as possible. You should follow the thought process:

1. What is the source input, and what requirements should it meet?
2. What is the follow-up input, and what requirements should it meet?
3. What is the relationship between the source input and the follow-up input, and what operations can be performed to transform the source input into the follow-up input?
4. What should be the source output corresponding to the source input?
5. What should be the follow-up output corresponding to the follow-up input?
6. What relationship should be satisfied between the source and follow-up outputs?

For example, an MR for sine function is:

- Source input: a float value $x$.
- Follow-up input: a float value $x+2\pi$.
- Input relation: The follow-up input can be obtained by adding $2\pi$ to the source input.
- Source output: a float value $sin(x)$.
- Follow-up output: a float value $sin(x+2\pi)$.
- Output relation: The source and follow-up outputs should be equal.

Note that only output one MR that you think is most accurate. The format of input and output should be as follows：

User:
[Text from the specification of [Driver name]]

Desired output:
```markdown
MR1: [Abstract of this MR]
- Source input: [Describe the source input]
- Follow-up input: [Describe the follow-up input]
- Input relation: [Describe how to transform source input into follow-up input]
- Souce output: [Describe the source output corresponding to the source input]
- Follow-up output: [Describe the follow-up output corresponding to the follow-up input]
- Output relation: [Describe output relation]
```
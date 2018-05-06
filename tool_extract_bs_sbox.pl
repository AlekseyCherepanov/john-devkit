#! /usr/bin/perl -0777
# Tool to extract bitslice formulas for DES s-boxes from John the Ripper's code
# Writes output to ./sboxes/*

# Copyright © 2015 Aleksey Cherepanov <lyosha@openwall.com>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

use strict;
use warnings;

my $input = <>;

my @inputs = qw/a1 a2 a3 a4 a5 a6/;

my @sboxes;

# Parsing
while ($input =~ /^s(\d) \( [^)]+ \) \s+ \{ ([^}]+) \}/gmx) {
    my $sbox_num = $1;
    my $code = $2;
    my @ops;
    my @outputs;
    while ($code =~ /v(\w+)\(([^\)]+)\)/gm) {
        my $op = $1;
        my $args = $2;
        my @args = split /,\s*/, $args;
        if ($args =~ /\*out\d/) {
            die "unexpected op for out: $op" if $op ne 'xor';
            push @outputs, $args[2];
        } else {
            push @ops, [$op, @args];
        }
    }
    push @sboxes, [$sbox_num, [@ops], @outputs];
}

my @new_sboxes;

my $name_counter = 0;
sub new_name {
    "var" . $name_counter++
}

my %op_names = qw/xor __xor__ and __and__ not __invert__ sel bit_select or __or__ andn andnot/;

# Renaming:
# - we don't reuse variables for assignment, we assign only once
# - we have other names for ops
# - we add 'input' and 'output' ops
for my $sbox (@sboxes) {
    my ($sbox_num, $ops, @outputs) = @$sbox;
    my @new_ops;
    my %substs;
    for my $i (@inputs) {
        # We drop input names.
        $substs{$i} = new_name;
        push @new_ops, ["input", $substs{$i}];
    }
    for my $op_vec (@$ops) {
        my ($op, @args) = @$op_vec;
        my $new_op = $op_names{$op};
        die "unknown op: $op" unless $new_op;
        my $nname = new_name;
        # There can be "xor a a b", so we remember new name only after the op.
        push @new_ops, [$new_op, $nname, map { $substs{$_} } @args[1 .. $#args]];
        $substs{$args[0]} = $nname;
    }
    @outputs = sort {
        my ($an, $bn) = map { /(\d+)/g } $a, $b;
        $an <=> $bn
    } @outputs;
    for my $o (@outputs) {
        push @new_ops, ["output", $substs{$o}];
    }
    push @new_sboxes, [$sbox_num, $#$ops + 1, $#inputs + 1, $#outputs + 1, @new_ops];
}


my %op_funcs = (
    '__invert__' => sub { (~$_[0]) & 1 },
    '__xor__' => sub { $_[0] ^ $_[1] },
    '__or__' => sub { $_[0] | $_[1] },
    '__and__' => sub { $_[0] & $_[1] },
    'andnot' => sub { ($_[0] & ~$_[1]) & 1 },
);

# Evaluate sbox for all possible values to get an array (look up table)
sub sbox_to_array {
    shift;
    shift;
    my ($n_inputs, $n_outputs, @ops) = @_;
    map {
        # warn "input: $_\n";
        my $input = $_;
        # Input into bits
        my @input_bits = reverse map { ($input >> $_) & 1 } 0 .. $n_inputs - 1;
        my @output_bits;
        my %values;
        for my $op_vec (@ops) {
            my ($op, @args) = @$op_vec;
            # warn "op: $op @args\n";
            if ($op eq 'input') {
                $values{$args[0]} = shift @input_bits;
            } elsif ($op eq 'output') {
                push @output_bits, $values{$args[0]};
            } else {
                my $op_func = $op_funcs{$op};
                die "op not implemented: $op" unless $op_func;
                $values{$args[0]} = $op_func->(map { $values{$_} } @args[1 .. $#args]);
                # warn $values{$args[0]};
            }
        }
        # bits to output
        my $r = 0;
        for (@output_bits) {
            $r <<= 1;
            $r |= $_;
        }
        $r
    } 0 .. 2 ** $n_inputs - 1;
}

# Output
# file name: sboxes/table.ni_no.len.comment
for my $sbox (@new_sboxes) {
    my @t = sbox_to_array(@$sbox);
    my ($sbox_num, $len, $ins, $outs, @ops) = @$sbox;
    my $name = join "_", @t;
    $name .= ".${ins}_$outs.$len.s$sbox_num";
    $name = "sboxes/$name";
    my $k = 0;
    $k++ while -e "$name.$k";
    $name .= ".$k";
    open my $f, '>', $name;
    for (@ops) {
        print $f "@$_\n";
    }
    close $f;
}
